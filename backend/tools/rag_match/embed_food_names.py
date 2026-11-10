"""Embed benchmark food names offline with a local quantized multilingual E5 ONNX model."""

import argparse
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from zipfile import BadZipFile

import numpy as np

from match import output_lock, read_json
from week1_snapshot import validate_snapshot


PROTOCOL = "e5-name-only-mean-pool-v1"
MODEL_FILE = Path("onnx/model_quantized.onnx")
TOKENIZER_FILE = Path("tokenizer.json")


def file_digest(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def prepare_inputs(snapshot, baseline):
    validate_snapshot(snapshot)
    if baseline.get("snapshotId") != snapshot["snapshotId"]:
        raise ValueError("The benchmark belongs to a different frozen snapshot.")
    rows = snapshot["rows"]
    by_code = {row["food_cd"]: row for row in rows}
    raw = [(r["food_cd"], r["food_nm"]) for r in rows if r["food_lv7cd"] == "01"]
    query_codes = {r["targetCd"] for r in baseline["referenceResults"]}
    query_codes.update(r["targetCd"] for r in baseline["partChecks"]["cases"])
    queries = []
    for code in sorted(query_codes):
        row = by_code[code]
        if row["food_lv7cd"] == "01":
            raise ValueError(f"Raw food cannot also be a benchmark query: {code}")
        queries.append((code, row["food_nm"]))
    if not raw or not queries:
        raise ValueError("The candidate corpus and the query set must both be nonempty.")
    return raw, queries


def prefixed_name(name, role):
    if not isinstance(name, str) or not name.strip():
        raise ValueError("A nonempty original food name is required.")
    return role + ": " + name.replace("_", " ")


def mean_pool(hidden, mask):
    if hidden.ndim != 3 or hidden.shape[:2] != mask.shape or hidden.shape[2] != 384:
        raise ValueError(f"Expected multilingual-e5-small token states [batch, tokens, 384]; got {hidden.shape}.")
    counts = mask.sum(axis=1, keepdims=True)
    if np.any(counts == 0):
        raise ValueError("Tokenizer returned an empty attention mask.")
    pooled = np.sum(hidden * mask[:, :, None].astype(np.float32), axis=1) / counts.astype(np.float32)
    norms = np.linalg.norm(pooled, axis=1, keepdims=True)
    if not np.all(np.isfinite(norms)) or np.any(norms <= 0):
        raise ValueError("Model returned a zero or non-finite sentence vector.")
    return np.asarray(pooled / norms, dtype=np.float32)


class Encoder:
    def __init__(self, graph, tokenizer_file, threads):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        self.tokenizer = Tokenizer.from_file(str(tokenizer_file))
        self.tokenizer.no_padding()
        self.tokenizer.enable_truncation(max_length=512)
        self.pad_id = self.tokenizer.token_to_id("<pad>")
        if self.pad_id is None:
            raise ValueError("The E5 tokenizer must define <pad>.")
        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(graph), sess_options=options, providers=["CPUExecutionProvider"])
        self.inputs = {node.name: node.type for node in self.session.get_inputs()}
        if not {"input_ids", "attention_mask"} <= self.inputs.keys() <= {"input_ids", "attention_mask", "token_type_ids"}:
            raise ValueError(f"Unsupported ONNX input names: {list(self.inputs)}")
        if not set(self.inputs.values()) <= {"tensor(int64)", "tensor(int32)"}:
            raise ValueError(f"Unsupported ONNX input types: {self.inputs}")
        outputs = [node.name for node in self.session.get_outputs()
                   if node.name in {"last_hidden_state", "token_embeddings"} and len(node.shape) == 3]
        if len(outputs) != 1:
            raise ValueError(f"Expected one named ONNX token-state output, found {outputs}.")
        self.output_name = outputs[0]

    def encode(self, texts, batch_size):
        # Identical names must get identical vectors, including with dynamic quantization.
        unique = list(dict.fromkeys(texts))
        encodings = self.tokenizer.encode_batch(unique)
        order = sorted(range(len(unique)), key=lambda i: (len(encodings[i].ids), unique[i]))
        vectors = np.empty((len(unique), 384), dtype=np.float32)
        for offset in range(0, len(order), batch_size):
            batch = order[offset:offset + batch_size]
            width = max(len(encodings[i].ids) for i in batch)
            ids = np.full((len(batch), width), self.pad_id, dtype=np.int64)
            mask = np.zeros_like(ids)
            segments = np.zeros_like(ids)
            for slot, index in enumerate(batch):
                item = encodings[index]
                size = len(item.ids)
                ids[slot, :size] = item.ids
                mask[slot, :size] = item.attention_mask
                segments[slot, :size] = item.type_ids
            columns = {"input_ids": ids, "attention_mask": mask, "token_type_ids": segments}
            feeds = {key: columns[key].astype(np.int64 if kind == "tensor(int64)" else np.int32, copy=False)
                     for key, kind in self.inputs.items()}
            hidden = self.session.run([self.output_name], feeds)[0]
            vectors[batch] = mean_pool(hidden, mask)
            if offset and offset % (batch_size * 20) == 0:
                print(f"Embedded {min(offset + batch_size, len(order))}/{len(order)} distinct texts", flush=True)
        index_by_text = {text: i for i, text in enumerate(unique)}
        return vectors[[index_by_text[text] for text in texts]]


def matches_cache(path, fingerprint, raw_codes, query_codes):
    with np.load(path, allow_pickle=False) as saved:
        if str(saved["fingerprint"].item()) != fingerprint:
            return False
        for prefix, expected in (("raw", raw_codes), ("query", query_codes)):
            if not np.array_equal(saved[prefix + "_codes"], expected):
                return False
            matrix = saved[prefix + "_vectors"]
            if matrix.dtype != np.float32 or matrix.shape != (len(expected), 384):
                return False
            if not np.allclose(np.linalg.norm(matrix, axis=1), 1, rtol=1e-5, atol=1e-6):
                return False
    return True


def valid_cache(path, fingerprint, raw_codes, query_codes):
    if not path.is_file():
        return False
    try:
        return matches_cache(path, fingerprint, raw_codes, query_codes)
    except (BadZipFile, EOFError, KeyError, OSError, ValueError):
        return False


def write_vectors(path, **fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".npz", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        np.savez_compressed(tmp_path, **fields)
        os.replace(tmp_path, path)
    finally:
        tmp_path.unlink(missing_ok=True)


def run(args):
    graph = args.model_dir / MODEL_FILE
    tokenizer = args.model_dir / TOKENIZER_FILE
    if args.output.resolve() in {p.resolve() for p in (args.snapshot, args.baseline, graph, tokenizer)}:
        raise ValueError("Use a separate output path for the vectors.")
    snapshot = read_json(args.snapshot)
    raw, queries = prepare_inputs(snapshot, read_json(args.baseline))
    raw_codes = np.asarray([code for code, _ in raw], dtype=np.str_)
    query_codes = np.asarray([code for code, _ in queries], dtype=np.str_)
    texts = [prefixed_name(name, "passage") for _, name in raw] + [prefixed_name(name, "query") for _, name in queries]
    identity = {
        "protocol": PROTOCOL, "model": args.model, "revision": args.revision,
        "snapshot_id": snapshot["snapshotId"], "model_sha256": file_digest(graph),
        "tokenizer_sha256": file_digest(tokenizer), "batch_size": args.batch_size,
        "threads": args.threads, "onnxruntime": version("onnxruntime"),
        "tokenizers": version("tokenizers"), "numpy": np.__version__,
    }
    contents = json.dumps([identity, raw_codes.tolist(), query_codes.tolist(), texts], ensure_ascii=False,
                          separators=(",", ":"), sort_keys=True)
    fingerprint = hashlib.sha256(contents.encode("utf-8")).hexdigest()
    with output_lock(args.output):
        if valid_cache(args.output, fingerprint, raw_codes, query_codes):
            print(f"Reused cached vectors: {args.output}")
            return
        started = time.perf_counter()
        encoder = Encoder(graph, tokenizer, args.threads)
        vectors = encoder.encode(texts, args.batch_size)
        seconds = time.perf_counter() - started
        write_vectors(args.output, **identity, fingerprint=fingerprint, inference_seconds=seconds,
                      raw_codes=raw_codes, raw_vectors=vectors[:len(raw)],
                      query_codes=query_codes, query_vectors=vectors[len(raw):])
        print(f"Encoded {len(raw)} raw records and {len(queries)} queries in {seconds:.1f}s: {args.output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for path in ("snapshot", "baseline", "model-dir", "output"):
        parser.add_argument("--" + path, type=Path, required=True)
    parser.add_argument("--model", default="Xenova/multilingual-e5-small")
    parser.add_argument("--revision", required=True, help="Exact Hugging Face repository commit SHA.")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--threads", type=int, default=min(6, os.cpu_count() or 1))
    args = parser.parse_args()
    if not re.fullmatch(r"[a-fA-F0-9]{40}", args.revision) or min(args.batch_size, args.threads) < 1:
        parser.error("Supply a 40-character model revision, positive batch size and thread count.")
    run(args)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, ImportError) as exc:
        sys.exit(f"Local embedding failed: {exc}")
