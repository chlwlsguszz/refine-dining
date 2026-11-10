"""Measure name-only retrieval on explicit pairs from the frozen food snapshot."""

import argparse
from collections import Counter
import math
from pathlib import Path
import sys

from benchmark_cases import build_reference_pairs
from benchmark_parts import run_part_checks
from blind_retrieval import NameSearch
from match import read_json, save_report
from week1_cohort import family_codes
from week1_snapshot import validate_snapshot


def rank_bounds(scores, index):
    """Best/worst possible rank of the reference; a zero score was never retrieved."""
    reference = scores[index]
    if reference <= 0:
        return None, None
    higher = tied = 0
    for score in scores:
        if math.isclose(score, reference, rel_tol=1e-12, abs_tol=1e-12):
            tied += 1
        elif score > reference:
            higher += 1
    return higher + 1, higher + tied


def split_references(pairs, manifest_rows, by_code):
    # Link codes sharing a normalized official family name, as in the frozen split.
    labeled_rows = [by_code[p["targetCd"]] for p in pairs]
    cohort_rows = [by_code[r["targetCd"]] for r in manifest_rows]
    families = family_codes(cohort_rows + labeled_rows)
    test_families = {families[row["lv4Cd"]] for row in manifest_rows if row["split"] == "test"}
    unresolved = {row["targetCd"] for row in manifest_rows}
    if any(pair["targetCd"] in unresolved for pair in pairs):
        raise ValueError("An unresolved discovery target was included as a reference.")
    allowed = [pair for pair in pairs if families[pair["familyCode"]] not in test_families]
    return allowed, len(pairs) - len(allowed), families, test_families


def measure(snapshot, manifest):
    validate_snapshot(snapshot)
    if snapshot["snapshotId"] != manifest["snapshotId"]:
        raise ValueError("The split and the source must reference the same snapshot.")
    rows = snapshot["rows"]
    by_code = {row["food_cd"]: row for row in rows}
    raw = [row for row in rows if row["food_lv7cd"] == "01"]
    positions = {row["food_cd"]: i for i, row in enumerate(raw)}
    search = NameSearch([row["food_nm"] for row in raw])
    pairs = build_reference_pairs(rows)
    allowed, withheld, families, test_families = split_references(pairs, manifest["rows"], by_code)
    if not allowed:
        raise ValueError("No eligible reference pairs outside the held-out families.")

    results = []
    for pair in allowed:
        scores = search.scores(pair["targetName"])
        best, worst = rank_bounds(scores, positions[pair["rawCd"]])
        highest = max(scores)
        # Sorting here is for displaying equally scored names, never for measuring a hit.
        top = sorted((raw[i]["food_nm"], raw[i]["food_cd"]) for i, score in enumerate(scores)
                     if highest > 0 and math.isclose(score, highest, rel_tol=1e-12, abs_tol=1e-12))
        results.append({**pair, "rankBest": best, "rankWorst": worst,
                        "firstPlaceCandidates": [{"foodCd": code, "foodNm": name} for name, code in top]})

    checks = run_part_checks(rows)
    for case in checks["cases"]:
        target = by_code[case["targetCd"]]
        for record in (target, by_code[case["rawCd"]]):
            family = record["food_lv4cd"]
            if families.get(family, family) in test_families:
                raise ValueError(f"Part-check record belongs to a held-out family: {record['food_cd']}")
        scores = search.scores(target["food_nm"])
        case["rankBest"], case["rankWorst"] = rank_bounds(scores, positions[case["rawCd"]])

    hits = {}
    for k in (1, 5):
        hits[str(k)] = {
            "guaranteed": sum(r["rankWorst"] is not None and r["rankWorst"] <= k for r in results),
            "possibleIncludingTies": sum(r["rankBest"] is not None and r["rankBest"] <= k for r in results),
        }
    return {
        "protocol": "name-only-reference-pairs-v1", "snapshotId": snapshot["snapshotId"],
        "splitProtocol": manifest["protocol"], "splitSeed": manifest["seed"],
        "retrieval": {"inputs": ["food_nm"], "method": "BM25 on words + Korean character bigrams",
                      "tiePolicy": "A guaranteed hit places the whole tie group inside k; zero scores are not retrieved."},
        "summary": {
            "rawSearchPool": len(raw), "totalReferencePairs": len(pairs), "withheldPairs": withheld,
            "evaluatedPairs": len(results), "distinctRawReferences": len({r["rawCd"] for r in results}),
            "evaluatedFamilies": len({families[r["familyCode"]] for r in results}),
            "byProcessingMethod": dict(sorted(Counter(r["method"] for r in results).items())),
            "hitsAt": hits,
        },
        "referenceResults": results, "partChecks": checks,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("snapshot", "split", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve() in {args.snapshot.resolve(), args.split.resolve()}:
        parser.error("The report must be separate from its input files.")
    result = measure(read_json(args.snapshot), read_json(args.split))
    save_report(args.output, result)
    print(result["summary"])
    print(result["partChecks"]["metrics"])


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        sys.exit(f"Name benchmark failed: {exc}")
