"""Compare lexical, dense and reciprocal-rank retrieval on the saved name-only benchmark."""

import argparse
from collections import Counter
import math
from pathlib import Path
import sys

import numpy as np

from blind_retrieval import NameSearch
from match import read_json, save_report
from week1_snapshot import validate_snapshot


METHODS = ("lexical", "dense", "hybrid")
RRF_CONSTANT = 60
DENSE_TOLERANCE = 1e-6  # The supplied embeddings use float32.


class Ranking:
    """Rank all positive scores, retaining the inclusive range occupied by each tied group."""

    def __init__(self, values, tolerance=1e-12):
        self.scores = np.asarray(values, dtype=np.float64)
        if self.scores.ndim != 1 or not np.isfinite(self.scores).all():
            raise ValueError("Expected one finite score per document.")
        self.first = np.zeros(self.scores.size, dtype=np.int32)
        self.last = np.zeros_like(self.first)
        positions = np.flatnonzero(self.scores > 0)
        order = positions[np.argsort(-self.scores[positions], kind="stable")]
        start = 0
        while start < len(order):
            end = start + 1
            anchor = self.scores[order[start]]
            # Compare against the highest score in this group, avoiding transitive tie chains.
            while end < len(order) and math.isclose(anchor, self.scores[order[end]],
                                                     rel_tol=tolerance, abs_tol=tolerance):
                end += 1
            self.first[order[start:end]] = start + 1
            self.last[order[start:end]] = end
            start = end

    def contribution(self):
        values = np.zeros_like(self.scores)
        retrieved = self.first > 0
        midranks = (self.first[retrieved] + self.last[retrieved]) / 2
        values[retrieved] = 1 / (RRF_CONSTANT + midranks)
        return values

    def describe(self, position, candidates):
        top = sorted((candidates[i]["food_nm"], candidates[i]["food_cd"])
                     for i in np.flatnonzero(self.first == 1))
        return {"rankBest": int(self.first[position]) or None, "rankWorst": int(self.last[position]) or None,
                "firstPlaceCandidates": [{"foodCd": code, "foodNm": name} for name, code in top]}


def read_text(archive, name):
    value = archive[name]
    if value.size != 1 or value.dtype.kind != "U" or not str(value.item()).strip():
        raise ValueError(f"Invalid metadata: {name}")
    return str(value.item())


def embedding_provenance(archive):
    data = {key: read_text(archive, key) for key in ("model", "revision", "snapshot_id")}
    for key in ("protocol", "model_sha256", "tokenizer_sha256", "fingerprint", "onnxruntime", "tokenizers", "numpy"):
        if key in archive:
            data[key] = read_text(archive, key)
    for key in ("batch_size", "threads"):
        if key in archive:
            value = archive[key]
            if value.size != 1 or value.dtype.kind not in "iu" or int(value.item()) < 1:
                raise ValueError(f"Invalid embedding configuration: {key}")
            data[key] = int(value.item())
    return data


def ordered_vectors(archive, prefix, expected_codes):
    codes = archive[prefix + "_codes"]
    vectors = archive[prefix + "_vectors"]
    if codes.ndim != 1 or codes.dtype.kind != "U":
        raise ValueError(f"{prefix}_codes must be a one-dimensional Unicode array.")
    positions = {code: i for i, code in enumerate(codes.tolist())}
    if len(positions) != len(codes) or set(positions) != set(expected_codes):
        raise ValueError(f"{prefix} codes differ from the complete frozen pool or are duplicated.")
    if (vectors.ndim != 2 or vectors.shape[0] != len(codes) or vectors.shape[1] == 0
            or vectors.dtype.kind != "f" or not np.isfinite(vectors).all()):
        raise ValueError(f"Invalid {prefix} embedding matrix.")
    ordered = vectors[[positions[code] for code in expected_codes]].astype(np.float64)
    lengths = np.linalg.norm(ordered, axis=1)
    if not np.isfinite(lengths).all() or (lengths == 0).any():
        raise ValueError(f"Invalid {prefix} embedding norm.")
    return ordered / lengths[:, None]


def require_baseline(snapshot, baseline, rows, raw):
    if baseline["snapshotId"] != snapshot["snapshotId"] or baseline["protocol"] != "name-only-reference-pairs-v1":
        raise ValueError("The name benchmark does not reference this frozen snapshot/protocol.")
    positives = baseline["referenceResults"]
    summary = baseline["summary"]
    if (not positives or len(positives) != summary["evaluatedPairs"] or len(raw) != summary["rawSearchPool"]
            or len({r["targetCd"] for r in positives}) != len(positives)):
        raise ValueError("Name benchmark has inconsistent counts or duplicate positive targets.")
    for case in [*positives, *baseline["partChecks"]["cases"]]:
        target = rows[case["targetCd"]]
        candidate = rows[case["rawCd"]]
        if (target["food_lv7cd"] == "01" or candidate["food_lv7cd"] != "01"
                or target["food_nm"] != case["targetName"] or candidate["food_nm"] != case["rawName"]):
            raise ValueError(f"Incorrect target/reference for {case['targetCd']}.")


def hits(rows, method, k, field="rankWorst"):
    return {row["targetCd"] for row in rows
            if row["methods"][method][field] is not None and row["methods"][method][field] <= k}


def summarize(rows):
    methods, changes = {}, {}
    for method in METHODS:
        methods[method] = {"hitsAt": {}}
        if method != "lexical":
            changes[method] = {}
        for k in (1, 5):
            found = hits(rows, method, k)
            methods[method]["hitsAt"][str(k)] = {
                "guaranteed": len(found),
                "possibleIncludingTies": len(hits(rows, method, k, "rankBest")),
            }
            if method != "lexical":
                before = hits(rows, "lexical", k)
                changes[method][str(k)] = {"recovered": sorted(found - before), "lost": sorted(before - found)}
    return {"methods": methods, "changesAgainstLexical": changes}


def compare(snapshot, baseline, vectors_path):
    validate_snapshot(snapshot)
    rows = {row["food_cd"]: row for row in snapshot["rows"]}
    raw = [row for row in snapshot["rows"] if row["food_lv7cd"] == "01"]
    positions = {row["food_cd"]: i for i, row in enumerate(raw)}
    require_baseline(snapshot, baseline, rows, raw)
    reference = [dict(row) for row in baseline["referenceResults"]]
    parts = [dict(row) for row in baseline["partChecks"]["cases"]]
    cases = {}
    for case in [*reference, *parts]:
        cases.setdefault(case["targetCd"], []).append(case)
    query_codes = sorted(cases)
    with np.load(vectors_path, allow_pickle=False) as archive:
        provenance = embedding_provenance(archive)
        if provenance["snapshot_id"] != snapshot["snapshotId"]:
            raise ValueError("Embedding archive and snapshot IDs differ.")
        queries = ordered_vectors(archive, "query", query_codes)
        documents = ordered_vectors(archive, "raw", list(positions))
    if queries.shape[1] != documents.shape[1]:
        raise ValueError("Query and document embedding dimensions differ.")
    similarities = queries @ documents.T
    lexical_index = NameSearch([row["food_nm"] for row in raw])
    for i, code in enumerate(query_codes):
        lexical = Ranking(lexical_index.scores(rows[code]["food_nm"]))
        dense = Ranking(similarities[i], DENSE_TOLERANCE)
        hybrid = Ranking(lexical.contribution() + dense.contribution())
        for case in cases[code]:
            position = positions[case["rawCd"]]
            case["methods"] = {name: ranking.describe(position, raw)
                               for name, ranking in zip(METHODS, (lexical, dense, hybrid))}
            reproduced = case["methods"]["lexical"]
            if reproduced["rankBest"] != case["rankBest"] or reproduced["rankWorst"] != case["rankWorst"]:
                raise ValueError(f"Lexical baseline rank failed to reproduce for {code} / {case['rawCd']}.")
            for field in ("rankBest", "rankWorst", "firstPlaceCandidates"):
                case.pop(field, None)

    summary = summarize(reference)
    if summary["methods"]["lexical"]["hitsAt"] != baseline["summary"]["hitsAt"]:
        raise ValueError("Lexical baseline hit counts failed to reproduce.")
    conflicts = [case for case in parts if case["expectedStatus"] == "conflict"]
    top_conflicts = {method: {str(k): sum(1 for c in conflicts if c["methods"][method]["rankWorst"] is not None
                                         and c["methods"][method]["rankWorst"] <= k) for k in (1, 5)}
                     for method in METHODS}
    return {
        "protocol": "name-only-local-vector-comparison-v1", "snapshotId": snapshot["snapshotId"],
        "baselineProtocol": baseline["protocol"], "splitProtocol": baseline["splitProtocol"],
        "splitSeed": baseline["splitSeed"], "model": provenance["model"], "revision": provenance["revision"],
        "embedding": provenance,
        "embeddingDimensions": int(documents.shape[1]), "rrfConstant": RRF_CONSTANT,
        "rankPolicy": "Positive scores only; inclusive tie intervals. Dense ties use 1e-6 relative/absolute "
                      "tolerance; lexical and RRF use 1e-12. RRF uses mean tied rank over all positive scores.",
        "summary": {**{k: v for k, v in baseline["summary"].items() if k != "hitsAt"}, **summary},
        "referenceResults": reference,
        "partChecks": {"guardMetrics": baseline["partChecks"]["metrics"],
                       "caseCounts": dict(Counter(row["expectedStatus"] for row in parts)),
                       "conflictPairsInTopKBeforeGuard": top_conflicts, "cases": parts},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("snapshot", "baseline", "vectors", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve() in {args.snapshot.resolve(), args.baseline.resolve(), args.vectors.resolve()}:
        parser.error("Output cannot overwrite the inputs.")
    report = compare(read_json(args.snapshot), read_json(args.baseline), args.vectors)
    save_report(args.output, report)
    print(report["summary"]["methods"])


if __name__ == "__main__":
    try:
        main()
    except (OSError, TypeError, KeyError, ValueError) as exc:
        sys.exit(f"Dense comparison failed: {exc}")
