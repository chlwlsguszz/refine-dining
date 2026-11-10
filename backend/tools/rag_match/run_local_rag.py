"""Run the frozen local matcher over an ordered retrieval result; no external inference."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, Request, build_opener

from assess_development import verify_record
from grounded_rag import (POLICY, PROMPT, compare_records, explain_generation, model_input, response_schema,
                          retrieve_passages, summarize, validate_generation, validate_passages)
from match import NoRedirect, ROOT, output_lock, read_json, save_report
from week1_snapshot import validate_snapshot


DATA = ROOT / "datasets/week1/2026-11-10"
MODEL = {"alias": "refine-qwen3", "repo": "Qwen/Qwen3-8B-GGUF", "file": "Qwen3-8B-Q5_K_M.gguf",
         "revision": "7c41481f57cb95916b40956ab2f0b139b296d974",
         "sha256": "068bae163faa96ad48032daf4e071a6a28fe67d8dcc95367609c2ff165e52738"}
GENERATION = {"temperature": 0, "seed": 42, "max_tokens": 384, "chat_template_kwargs": {"enable_thinking": False}}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


class LocalLlama:
    def __init__(self, endpoint):
        uri = urlsplit(endpoint)
        if (uri.scheme != "http" or uri.hostname not in {"127.0.0.1", "::1"} or uri.username or uri.password
                or uri.path.rstrip("/") or uri.query or uri.fragment):
            raise ValueError("Use the numeric HTTP loopback base URL of llama-server.")
        self.base = endpoint.rstrip("/")
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def request(self, path, body=None, timeout=45):
        data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
        req = Request(self.base + path, data=data, headers={"Content-Type": "application/json"})
        with self.opener.open(req, timeout=timeout) as response:
            return json.load(response)

    def verify(self):
        props = self.request("/props", timeout=5)
        if props["model_alias"] != MODEL["alias"] or not props.get("build_info"):
            raise ValueError("Unexpected local llama.cpp alias or missing build revision.")
        model_file = Path(props["model_path"])
        with model_file.open("rb") as stream:
            checksum = hashlib.file_digest(stream, "sha256").hexdigest()
        if checksum != MODEL["sha256"]:
            raise ValueError("Unexpected GGUF weights.")
        return {"serverBuild": props["build_info"], "contextSize": props["default_generation_settings"]["n_ctx"],
                "chatTemplateHash": digest(props["chat_template"]), **MODEL}

    def generate(self, payload, schema):
        body = {**GENERATION, "model": MODEL["alias"], "messages": [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":"))}],
            "response_format": {"type": "json_schema", "json_schema": {"name": "food_proposal", "strict": True,
                                                                        "schema": schema}}}
        result = self.request("/v1/chat/completions", body)
        choice = result["choices"][0]
        if choice["finish_reason"] != "stop":
            raise ValueError("incomplete_generation")
        return {"response": json.loads(choice["message"]["content"]), "usage": result["usage"]}


def generate_case(client, config, row, candidates, passages, allowed, cache_dir, unavailable):
    target = row["target"]
    payload = model_input(target, candidates, passages)
    schema = response_schema(target, candidates, passages)
    key = digest([config, payload, schema, row.get("boundaryTies")])
    cache = cache_dir / (key + ".json")
    start = time.perf_counter()
    hit = False
    try:
        if unavailable:
            return {"status": "unavailable", "error": unavailable, "cacheHit": False, "elapsedMs": 0}
        if cache.is_file():
            data = read_json(cache)
            if data.get("key") != key or not isinstance(data.get("response"), dict):
                raise ValueError("invalid_cache_record")
            hit = True
        else:
            data = {"key": key, **client.generate(payload, schema)}
            save_report(cache, data)
        elapsed = round(1000 * (time.perf_counter() - start), 3)
        result = {"response": data["response"], "usage": data["usage"], "cacheHit": hit, "cacheKey": key,
                  "elapsedMs": elapsed}
        # Read the just-written entry through the same JSON reader to measure a genuine warm cache lookup.
        warm = time.perf_counter()
        if read_json(cache) != data:
            raise ValueError("cache_verification_failed")
        result["warmReadMs"] = round(1000 * (time.perf_counter() - warm), 3)
        try:
            result["difference"] = validate_generation(data["response"], target, candidates, passages, allowed)
            result["explanation"] = explain_generation(data["response"], target, candidates, passages,
                                                       result["difference"])
            result["status"] = "validated"
        except ValueError as exc:
            result.update(status="rejected", error=str(exc))
        return result
    except (URLError, TimeoutError, OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        return {"status": "generation_error", "error": str(exc), "cacheHit": hit, "cacheKey": key,
                "elapsedMs": round(1000 * (time.perf_counter() - start), 3)}


def elapsed_stats(values):
    if not values:
        return {"count": 0}
    return {"count": len(values), "medianMs": round(statistics.median(values), 3),
            "totalMs": round(sum(values), 3), "maxMs": max(values)}


def run(ranking, corpus, snapshot, client, cache_dir):
    validate_snapshot(snapshot)
    validate_passages(corpus["passages"])
    if (ranking["snapshotId"] != snapshot["snapshotId"] or ranking["k"] != 5
            or not ranking.get("results")):
        raise ValueError("Expected a populated frozen top-five retrieval.")
    try:
        model, unavailable = client.verify(), None
    except (OSError, ValueError, KeyError, TypeError) as exc:
        model, unavailable = MODEL, str(exc)
    config = {"snapshotId": snapshot["snapshotId"], "policy": POLICY, "retrievalPolicy": ranking.get("policy"),
              "retrievalEncoder": ranking.get("model"), "retrievalRevision": ranking.get("revision"),
              "retrievalProtocol": ranking.get("protocol"), "k": ranking["k"],
              "passageVersion": corpus["version"], "passageHash": digest(corpus), "model": model,
              "promptSha256": digest(PROMPT), "generation": GENERATION}
    originals = {r["food_cd"]: r for r in snapshot["rows"]}
    outputs, seen = [], set()
    for entry in ranking["results"]:
        target = entry["target"]
        records = [item["record"] for item in entry["candidates"]]
        codes = [r["foodCd"] for r in records]
        if target["foodCd"] in seen or len(codes) > 5 or len(set(codes)) != len(codes):
            raise ValueError("Duplicate case, duplicate candidate, or invalid top-five size.")
        seen.add(target["foodCd"])
        verify_record(target, originals, False)
        for record in records:
            verify_record(record, originals, True)
        boundary = entry.get("boundaryTies", [])
        started = time.perf_counter()
        docs = retrieve_passages(target, corpus["passages"])
        doc_time = round(1000 * (time.perf_counter() - started), 3)
        baseline, allowed = compare_records(target, records, docs, len(boundary) if isinstance(boundary, list) else boundary)
        generation = generate_case(client, config, entry, records, docs, allowed, cache_dir, unavailable)
        # Keep verified suggestions as review proposals. Generation is an independently assessed explanation.
        # A model failure or a more conservative model abstention never approves a food pair.
        assessments = {a["foodCd"]: a for a in baseline["assessments"]}
        display = [{**item, "assessment": assessments[item["record"]["foodCd"]]["flag"],
                    "reason": assessments[item["record"]["foodCd"]]["reason"]} for item in entry["candidates"]]
        for item in display:
            if item["record"]["foodCd"] == allowed["selectedCd"]:
                item.update(assessment=("direct" if allowed["verdict"] == "직접 비교" else "reference"),
                            reason=allowed["reason"])
        outputs.append({"target": target, "targetCd": target["foodCd"], "targetQuote": target["foodNm"],
                        **allowed, "status": "unreviewed_proposal", "candidates": display,
                        "sourceRecords": {k: baseline[k] for k in ("selectedCd", "verdict", "reason")},
                        "withPassages": {k: allowed[k] for k in ("selectedCd", "verdict", "reason")},
                        "passageIds": [p["id"] for p in docs], "passageRetrievalMs": doc_time,
                        "generation": generation})
    generations = [r["generation"] for r in outputs]
    summary = {**summarize(outputs), "rows": len(outputs), "rowsWithPassages": sum(bool(r["passageIds"]) for r in outputs),
               "rejectionReasons": dict(Counter(g["error"] for g in generations if g["status"] == "rejected")),
               "passageSearch": elapsed_stats([r["passageRetrievalMs"] for r in outputs]),
               "localRequests": sum(not g["cacheHit"] and not unavailable for g in generations),
               "externalRequests": 0, "cacheHits": sum(g["cacheHit"] for g in generations),
               "modelAndCacheWrite": elapsed_stats([g["elapsedMs"] for g in generations if "warmReadMs" in g and not g["cacheHit"]]),
               "warmCacheRead": elapsed_stats([g["warmReadMs"] for g in generations if "warmReadMs" in g])}
    return {"snapshotId": snapshot["snapshotId"], "policyVersion": POLICY, "runConfig": config, "summary": summary,
            "results": outputs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DATA / "raw-snapshot.json")
    parser.add_argument("--retrieved", type=Path, required=True)
    parser.add_argument("--passages", type=Path, required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:18081")
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve() in {p.resolve() for p in (args.snapshot, args.passages, args.retrieved)}:
        parser.error("Output must be distinct from the frozen inputs.")
    with output_lock(args.output):
        report = run(read_json(args.retrieved), read_json(args.passages), read_json(args.snapshot),
                     LocalLlama(args.endpoint), args.cache_dir)
        save_report(args.output, report)
    print(json.dumps(report["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
