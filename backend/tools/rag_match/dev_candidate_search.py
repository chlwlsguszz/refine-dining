"""Retrieve five raw-food records per development query using local, name-only E5 cosine search."""

import argparse
from collections import Counter
from pathlib import Path
import sys

import numpy as np

from blind_retrieval import NameSearch
from compare_dense import DENSE_TOLERANCE, Ranking, embedding_provenance, ordered_vectors
from embed_food_names import Encoder, MODEL_FILE, PROTOCOL, TOKENIZER_FILE, file_digest, prefixed_name
from match import read_json, save_report
from week1_cohort import FIELDS
from week1_snapshot import validate_snapshot


MODEL = "Xenova/multilingual-e5-small"
REVISION = "761b726dd34fb83930e26aab4e9ac3899aa1fa78"
MODEL_SHA = "f80102d3f2a1229f387d3c81909990d8945513e347b0eab049f7de3c6f98c193"
TOKENIZER_SHA = "0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39"
TOP_K = 5


def development_rows(snapshot, split):
    if split["snapshotId"] != snapshot["snapshotId"]:
        raise ValueError("The frozen split and snapshot differ.")
    entries = split["rows"]
    counts = Counter(entry["split"] for entry in entries)
    if (set(counts) != {"dev_review", "dev_remaining", "test"} or counts != split["splitCounts"]
            or len(entries) != split["totalTargets"] or len({e["targetCd"] for e in entries}) != len(entries)):
        raise ValueError("Split membership or counts are inconsistent.")
    held_families = {entry["familyCode"] for entry in entries if entry["split"] == "test"}
    selected = sorted((e for e in entries if e["split"] != "test"), key=lambda e: e["targetCd"])
    if any(e["familyCode"] in held_families for e in selected):
        raise ValueError("A development family also belongs to the final evaluation split.")
    by_code = {r["food_cd"]: r for r in snapshot["rows"]}
    for entry in selected:
        row = by_code[entry["targetCd"]]
        if row["food_lv7cd"] == "01" or entry["targetNm"] != row["food_nm"]:
            raise ValueError(f"Unexpected target or changed original name: {entry['targetCd']}")
    return [(entry, by_code[entry["targetCd"]]) for entry in selected]


def source(row):
    return {key: row.get(field) for key, field in FIELDS.items()}


def top_candidates(similarities, lexical_scores, raw, k=TOP_K):
    dense = Ranking(similarities, DENSE_TOLERANCE)
    lexical = Ranking(lexical_scores)
    eligible = [i for i, rank in enumerate(dense.first) if 0 < rank <= k]
    # Code order decides display position only within equally ranked candidates.
    eligible.sort(key=lambda i: (dense.first[i], raw[i]["food_cd"]))
    records = [
        {"record": source(raw[i]), "score": float(dense.scores[i]), "rank": int(dense.first[i]),
         "rankWorst": int(dense.last[i]), "lexicalRank": int(lexical.first[i]) or None,
         "lexicalRankWorst": int(lexical.last[i]) or None}
        for i in eligible
    ]
    return records[:k], records[k:]


def retrieve(args):
    snapshot, split = read_json(args.snapshot), read_json(args.split)
    validate_snapshot(snapshot)
    queries = development_rows(snapshot, split)
    raw = [r for r in snapshot["rows"] if r["food_lv7cd"] == "01"]
    graph, tokenizer = args.model_dir / MODEL_FILE, args.model_dir / TOKENIZER_FILE
    with np.load(args.raw_vectors, allow_pickle=False) as archive:
        provenance = embedding_provenance(archive)
        expected = {"snapshot_id": snapshot["snapshotId"], "model": MODEL, "revision": REVISION,
                    "protocol": PROTOCOL, "model_sha256": MODEL_SHA, "tokenizer_sha256": TOKENIZER_SHA}
        if any(provenance.get(key) != value for key, value in expected.items()):
            raise ValueError("Passage cache provenance differs from the pinned E5 model or snapshot.")
        if file_digest(graph) != MODEL_SHA or file_digest(tokenizer) != TOKENIZER_SHA:
            raise ValueError("Local E5 model or tokenizer checksum mismatch.")
        passages = ordered_vectors(archive, "raw", [r["food_cd"] for r in raw])
    encoder = Encoder(graph, tokenizer, provenance["threads"])
    names = [prefixed_name(r["food_nm"], "query") for _, r in queries]
    vectors = encoder.encode(names, provenance["batch_size"]).astype(np.float64)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    similarities = vectors @ passages.T
    lexical = NameSearch([r["food_nm"] for r in raw])
    results = []
    for (entry, row), scores in zip(queries, similarities):
        candidates, boundary = top_candidates(scores, lexical.scores(row["food_nm"]), raw)
        results.append({"target": source(row), "family": entry["family"], "familyCode": entry["familyCode"],
                        "split": entry["split"], "stratum": entry["stratum"], "candidates": candidates,
                        "boundaryTies": boundary})
    return {"protocol": "development-dense-top5-v1", "snapshotId": snapshot["snapshotId"],
            "splitProtocol": split["protocol"], "splitSeed": split["seed"], "model": MODEL, "revision": REVISION,
            "k": TOP_K, "rawCount": len(raw), "queryCount": len(queries), "familyCount": len({e["familyCode"] for e, _ in queries}),
            "embedding": provenance, "inputFields": ["food_nm"], "tieTolerance": DENSE_TOLERANCE,
            "results": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("snapshot", "split", "model-dir", "raw-vectors", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    protected = (args.snapshot, args.split, args.raw_vectors, args.model_dir / MODEL_FILE, args.model_dir / TOKENIZER_FILE)
    if args.output.resolve() in {p.resolve() for p in protected}:
        parser.error("Use an output file distinct from all inputs.")
    report = retrieve(args)
    save_report(args.output, report)
    print(f"{report['queryCount']} development targets, {report['rawCount']} raw candidates, "
          f"{sum(len(r['candidates']) for r in report['results'])} displayed links, "
          f"{sum(len(r['boundaryTies']) for r in report['results'])} additional boundary ties.")


if __name__ == "__main__":
    try:
        main()
    except (KeyError, OSError, TypeError, ValueError) as exc:
        sys.exit(f"Development retrieval failed: {exc}")
