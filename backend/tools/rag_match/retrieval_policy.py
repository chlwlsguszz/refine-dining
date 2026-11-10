"""Compare retrieval policies on development data, then apply a frozen policy to a partition."""

import argparse
from collections import Counter
from pathlib import Path
import sqlite3
import time

import numpy as np

from assess_development import assess
from benchmark_parts import run_part_checks
from blind_retrieval import NameSearch
from compare_dense import DENSE_TOLERANCE, Ranking, embedding_provenance, ordered_vectors, require_baseline
from dev_candidate_search import MODEL, MODEL_SHA, REVISION, TOKENIZER_SHA, development_rows, source
from embed_food_names import Encoder, MODEL_FILE, PROTOCOL, TOKENIZER_FILE, file_digest, prefixed_name
from match import read_json, save_report
from week1_snapshot import validate_snapshot


ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "datasets/week1/2026-11-10"
OUTPUT = DATA / "retrieval-policy"
METHODS = ("global_e5", "family_e5", "hierarchy_sql", "family3_global")
VERSION = "food-retrieval-v1"
K = 5
FAMILY_SLOTS = 3
HIERARCHY_SQL = """
    SELECT position FROM raw_food
    WHERE src = ? AND family = ?
    ORDER BY CASE WHEN middle = ? THEN 0 ELSE 1 END, code
    LIMIT ?
"""


class Index:
    def __init__(self, raw):
        self.raw = raw
        self.families = {}
        self.sql = sqlite3.connect(":memory:")
        self.sql.execute("CREATE TABLE raw_food (position INTEGER, code TEXT, src TEXT, family TEXT, middle TEXT)")
        self.sql.executemany("INSERT INTO raw_food VALUES (?, ?, ?, ?, ?)",
                             ((i, r["food_cd"], r["src_cd"], r["food_lv4cd"], r["food_lv5cd"])
                              for i, r in enumerate(raw)))
        self.sql.execute("CREATE INDEX family_lookup ON raw_food(src, family)")
        for i, row in enumerate(raw):
            family = row["food_lv4cd"]
            if family:
                self.families.setdefault(family, set()).add(i)

    def search(self, method, row, scores):
        if method == "hierarchy_sql":
            matches = [i for i, in self.sql.execute(HIERARCHY_SQL, (
                row["src_cd"], row["food_lv4cd"], row["food_lv5cd"], K))]
            return matches, set(), set()

        order = Ranking(scores, DENSE_TOLERANCE)
        ordered = sorted(np.flatnonzero(order.first > 0), key=lambda i: (order.first[i], self.raw[i]["food_cd"]))
        family = self.families.get(row["food_lv4cd"], set())
        local = [i for i in ordered if i in family]
        if method == "family_e5":
            return take(local, K, order.first)
        if method == "global_e5":
            return take(ordered, K, order.first)
        if method != "family3_global":
            raise ValueError(f"Unknown policy {method}")
        selected, uncertain, boundary = take(local, FAMILY_SLOTS, order.first)
        used = set(selected)
        global_slots, extra_uncertain, extra_boundary = take([i for i in ordered if i not in used], K - len(selected), order.first)
        selected.extend(global_slots)
        # A candidate tied at the local boundary and independently selected by the global pass stays visible.
        hidden = (boundary | extra_boundary) - set(selected)
        return selected, (uncertain | extra_uncertain) if hidden else set(), hidden


def take(positions, limit, ranks):
    selected = positions[:limit]
    if not selected or len(positions) <= limit or ranks[selected[-1]] != ranks[positions[limit]]:
        return selected, set(), set()
    at_cut = ranks[selected[-1]]
    return selected, {i for i in selected if ranks[i] == at_cut}, {i for i in positions[limit:] if ranks[i] == at_cut}


def config(snapshot_id, method):
    return {"protocol": VERSION, "snapshotId": snapshot_id, "method": method, "k": K,
            "familySlots": FAMILY_SLOTS, "model": MODEL, "revision": REVISION, "modelSha256": MODEL_SHA,
            "tokenizerSha256": TOKENIZER_SHA, "embeddingProtocol": PROTOCOL, "tieTolerance": DENSE_TOLERANCE,
            "denseTiebreak": "food_cd", "familyField": "food_lv4cd", "sql": "same source/family, same middle first, food_cd"}


def catalog(args, baseline=None):
    snapshot, split = read_json(args.snapshot), read_json(args.split)
    validate_snapshot(snapshot)
    if split["snapshotId"] != snapshot["snapshotId"]:
        raise ValueError("Split and snapshot differ")
    raw = [r for r in snapshot["rows"] if r["food_lv7cd"] == "01"]
    graph, tokenizer = args.model_dir / MODEL_FILE, args.model_dir / TOKENIZER_FILE
    if file_digest(graph) != MODEL_SHA or file_digest(tokenizer) != TOKENIZER_SHA:
        raise ValueError("Incorrect local E5 model or tokenizer")
    with np.load(args.raw_vectors, allow_pickle=False) as cache:
        meta = embedding_provenance(cache)
        expected = {"snapshot_id": snapshot["snapshotId"], "model": MODEL, "revision": REVISION, "protocol": PROTOCOL,
                    "model_sha256": MODEL_SHA, "tokenizer_sha256": TOKENIZER_SHA}
        if any(meta.get(k) != v for k, v in expected.items()):
            raise ValueError("Incorrect E5 vector provenance")
        passages = ordered_vectors(cache, "raw", [r["food_cd"] for r in raw])
        easy = {}
        if baseline is not None:
            originals = {r["food_cd"]: r for r in snapshot["rows"]}
            require_baseline(snapshot, baseline, originals, raw)
            codes = sorted({c["targetCd"] for c in baseline["referenceResults"] + baseline["partChecks"]["cases"]})
            easy = dict(zip(codes, ordered_vectors(cache, "query", codes) @ passages.T))
    return snapshot, split, Index(raw), Encoder(graph, tokenizer, meta["threads"]), passages, meta, easy


def partition_rows(snapshot, split, partition):
    dev = development_rows(snapshot, split)
    if partition == "dev":
        return dev
    originals = {r["food_cd"]: r for r in snapshot["rows"]}
    return [(entry, originals[entry["targetCd"]]) for entry in sorted(split["rows"], key=lambda e: e["targetCd"])
            if entry["split"] == "test"]


def question_scores(entries, encoder, meta, passages):
    names = [prefixed_name(row["food_nm"], "query") for _, row in entries]
    vectors = encoder.encode(names, meta["batch_size"]).astype(np.float64)
    return (vectors / np.linalg.norm(vectors, axis=1, keepdims=True)) @ passages.T


def candidate_rows(index, entries, similarities, method, snapshot, split, lexical):
    output, elapsed = [], 0.0
    for (entry, row), scores in zip(entries, similarities):
        started = time.perf_counter()
        selected, uncertain, boundary = index.search(method, row, scores)
        elapsed += time.perf_counter() - started
        word_rank = Ranking(lexical.scores(row["food_nm"]))

        def record(i, position):
            return {"record": source(index.raw[i]), "rank": position, "rankWorst": None if i in uncertain else position,
                    "score": None if method == "hierarchy_sql" else float(scores[i]),
                    "lexicalRank": int(word_rank.first[i]) or None, "lexicalRankWorst": int(word_rank.last[i]) or None}

        output.append({**{k: entry[k] for k in ("family", "familyCode", "split", "stratum")}, "target": source(row),
                       "candidates": [record(i, pos) for pos, i in enumerate(selected, 1)],
                       "boundaryTies": [record(i, None) for i in sorted(boundary, key=lambda j: index.raw[j]["food_cd"])]})
    return {"protocol": VERSION, "snapshotId": snapshot["snapshotId"], "splitProtocol": split["protocol"],
            "splitSeed": split["seed"], "model": MODEL, "revision": REVISION, "k": K, "rawCount": len(index.raw),
            "queryCount": len(entries), "familyCount": len({e["familyCode"] for e, _ in entries}),
            "policy": method, "results": output}, elapsed


def regression(index, snapshot, baseline, similarities):
    originals = {r["food_cd"]: r for r in snapshot["rows"]}
    parts = run_part_checks(snapshot["rows"])
    results = []
    for case in baseline["referenceResults"] + parts["cases"]:
        code, expected = case["targetCd"], case["rawCd"]
        ranks = {}
        for method in METHODS:
            chosen, uncertain, _ = index.search(method, originals[code], similarities[code])
            found = next(((rank, i) for rank, i in enumerate(chosen, 1) if index.raw[i]["food_cd"] == expected), None)
            ranks[method] = {"position": found[0] if found else None, "guaranteedTop5": bool(found and found[1] not in uncertain)}
        results.append({"targetCd": code, "targetNm": originals[code]["food_nm"], "rawCd": expected,
                        "rawNm": originals[expected]["food_nm"], "case": case.get("expectedStatus", "reference"),
                        "ranks": ranks})
    return {"guard": parts["metrics"], "results": results,
            "guaranteedHitsAt5": {m: dict(Counter(r["case"] for r in results if r["ranks"][m]["guaranteedTop5"]))
                                  for m in METHODS}}


def compare(args):
    baseline = read_json(args.baseline)
    snapshot, split, index, encoder, passages, meta, easy = catalog(args, baseline)
    entries = development_rows(snapshot, split)
    started = time.perf_counter()
    scores = question_scores(entries, encoder, meta, passages)
    encoder_seconds = time.perf_counter() - started
    lexical = NameSearch([r["food_nm"] for r in index.raw])
    regression_report = regression(index, snapshot, baseline, easy)
    sources = read_json(args.evidence)["sources"]
    methods, stats, reviews = {}, {}, {}
    for method in METHODS:
        ranking, elapsed = candidate_rows(index, entries, scores, method, snapshot, split, lexical)
        review = assess(ranking, split, snapshot, sources)
        methods[method], reviews[method] = ranking, review["results"]
        stats[method] = {"rankingSeconds": elapsed, **review["summary"],
                         "shortLists": sum(len(r["candidates"]) < K for r in ranking["results"])}
    comparisons = []
    for pos, (_, row) in enumerate(entries):
        by_method, displayed = {}, {}
        for method in METHODS:
            item = reviews[method][pos]
            displayed[method] = [c["record"]["foodCd"] for c in item["candidates"]]
            by_method[method] = {
                "top5": [{"foodCd": c["record"]["foodCd"], "foodNm": c["record"]["foodNm"], "lv4Cd": c["record"]["lv4Cd"],
                          "rank": c["rank"], "assessment": c["assessment"], "reason": c["reason"]} for c in item["candidates"]],
                "selectedCd": item["selectedCd"], "verdict": item["verdict"], "reason": item["reason"]}
        for method in METHODS:
            old, new = displayed["global_e5"], displayed[method]
            by_method[method]["added"] = [c for c in new if c not in old]
            by_method[method]["lost"] = [c for c in old if c not in new]
        comparisons.append({"targetCd": row["food_cd"], "targetNm": row["food_nm"], "lv4Cd": row["food_lv4cd"], "methods": by_method})
    mixed = "family3_global"
    retained = all(r["methods"]["global_e5"]["selectedCd"] in (None, r["methods"][mixed]["selectedCd"]) for r in comparisons)
    safe_easy = all(not r["ranks"]["global_e5"]["guaranteedTop5"] or r["ranks"][mixed]["guaranteedTop5"]
                    for r in regression_report["results"] if r["case"] == "reference")
    fewer_wrong_families = stats[mixed]["queriesWithoutSameLv4InTop5"] < stats["global_e5"]["queriesWithoutSameLv4InTop5"]
    selected = mixed if retained and safe_easy and fewer_wrong_families else "global_e5"
    selection = {"method": selected, "criterion": "Keep family3_global if all baseline reference proposals remain, "
                 "no guaranteed easy top-5 hit is lost and development same-family coverage improves. Otherwise keep global_e5.",
                 "allPriorProposalsPreserved": retained, "noEasyHitsLost": safe_easy, "familyCoverageIncreased": fewer_wrong_families}
    report = {"protocol": VERSION, "snapshotId": snapshot["snapshotId"], "embedding": meta,
              "devQueryEncodingAndDotProductSeconds": encoder_seconds, "selection": selection, "summary": stats,
              "scope": "Same-family presence is a retrieval diagnostic. Development decisions are unapproved suggestions.",
              "developmentComparisons": comparisons, "regression": regression_report}
    save_report(args.output_dir / "comparison.json", report)
    save_report(args.output_dir / "development.json", methods[selected])
    save_report(args.output_dir / "policy.json", config(snapshot["snapshotId"], selected))
    print(selection)
    print("Easy + part top5", regression_report["guaranteedHitsAt5"])
    print("Development misses", {m: s["queriesWithoutSameLv4InTop5"] for m, s in stats.items()})


def infer(args):
    snapshot, split, index, encoder, passages, meta, _ = catalog(args)
    policy = read_json(args.policy)
    if policy.get("method") not in METHODS or policy != config(snapshot["snapshotId"], policy["method"]):
        raise ValueError("The frozen policy does not match this snapshot, model or procedure")
    entries = partition_rows(snapshot, split, args.partition)
    scores = question_scores(entries, encoder, meta, passages)
    lexical = NameSearch([r["food_nm"] for r in index.raw])
    result, _ = candidate_rows(index, entries, scores, policy["method"], snapshot, split, lexical)
    save_report(args.output, result)
    print(f"{args.partition}: {result['queryCount']} queries, {result['familyCount']} families, {result['policy']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    comparison = commands.add_parser("compare")
    inference = commands.add_parser("infer")
    for command in (comparison, inference):
        command.add_argument("--snapshot", type=Path, default=DATA / "raw-snapshot.json")
        command.add_argument("--split", type=Path, default=DATA / "review/split-manifest.json")
        command.add_argument("--model-dir", type=Path, default=ROOT / "backend/build/models/multilingual-e5-small" / REVISION)
        command.add_argument("--raw-vectors", type=Path, default=ROOT / "backend/build/e5-small-vectors.npz")
    comparison.add_argument("--baseline", type=Path, default=DATA / "name-benchmark.json")
    comparison.add_argument("--evidence", type=Path, default=DATA / "dev-matching/processing-evidence.json")
    comparison.add_argument("--output-dir", type=Path, default=OUTPUT)
    inference.add_argument("--policy", type=Path, default=OUTPUT / "policy.json")
    inference.add_argument("--partition", choices=("dev", "test"), required=True)
    inference.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "infer":
        if args.output.resolve() in {p.resolve() for p in (args.snapshot, args.split, args.policy, args.raw_vectors,
                                                          args.model_dir / MODEL_FILE, args.model_dir / TOKENIZER_FILE)}:
            parser.error("Output must differ from inputs")
        infer(args)
    else:
        compare(args)


if __name__ == "__main__":
    main()
