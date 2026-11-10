"""Apply the local comparison policy to the development retrieval run. No data or model calls."""

import argparse
from collections import Counter
from pathlib import Path
import sys

from dev_match_policy import decide
from match import known, read_json, save_report
from week1_cohort import FIELDS
from week1_snapshot import validate_snapshot


def verify_record(record, snapshot_rows, raw):
    row = snapshot_rows[record["foodCd"]]
    if ((row["food_lv7cd"] == "01") != raw or
            any(key not in record or record[key] != row.get(column) for key, column in FIELDS.items())):
        raise ValueError(f"Evidence differs from the frozen original: {record['foodCd']}")


def documented_reference(target, records, sources):
    """An ingredient definition supports a reference, not identity of samples or nutrient retention."""
    for source in sources:
        family, processed, state = source["family"], source["processed"], source["state"]
        if (target["foodNm"].split("_") != [family, processed, state]
                or (target["lv4Nm"], target["lv5Nm"], target["lv7Nm"]) != (family, processed, state)):
            continue
        ingredient = source["rawIngredient"]
        matches = [r for r in records if r["foodNm"].split("_") == [family, ingredient, "생것"]
                   and (r["lv4Nm"], r["lv5Nm"], r["lv7Cd"]) == (family, ingredient, "01")]
        if len(matches) != 1:
            return None
        raw = matches[0]
        if (not known(target["basis"]) or not known(target["srcCd"]) or target["imported"] not in ("Y", "N")
                or (target["imported"] == "Y" and not known(target["country"]))
                or any(target[f] != raw[f] for f in ("srcCd", "basis", "country", "imported", "region", "month"))):
            return None
        reason = (f"{source['summary']} 검색 후보 중 ‘{raw['foodNm']}’이 이 원료에 해당합니다. "
                  f"두 관측값은 각각 {target['basis']} 기준입니다. 이 정의로 두 표본의 산지·연근이나 동일 시료 여부까지 확인할 수는 없습니다.")
        return raw, source, reason
    return None


def assess(ranking, manifest, snapshot, sources=()):
    validate_snapshot(snapshot)
    if (ranking["snapshotId"] != snapshot["snapshotId"] or manifest["snapshotId"] != snapshot["snapshotId"]
            or ranking["k"] != 5 or ranking["splitProtocol"] != manifest["protocol"]
            or ranking["splitSeed"] != manifest["seed"]):
        raise ValueError("Inconsistent retrieval/split/snapshot configuration.")
    expected = {r["targetCd"]: r for r in manifest["rows"] if r["split"] in ("dev_review", "dev_remaining")}
    actual = [r["target"]["foodCd"] for r in ranking["results"]]
    if set(actual) != set(expected) or len(actual) != len(expected):
        raise ValueError("The retrieved set must cover development targets exactly once.")

    originals = {r["food_cd"]: r for r in snapshot["rows"]}
    results = []
    original_counts, verdict_counts, assessment_counts = Counter(), Counter(), Counter()
    for row in ranking["results"]:
        target = row["target"]
        verify_record(target, originals, raw=False)
        entry = expected[target["foodCd"]]
        if any(row[key] != entry[key] for key in ("family", "familyCode", "split", "stratum")):
            raise ValueError(f"Incorrect frozen family or split for {target['foodCd']}")
        retrieved = row["candidates"]
        boundary = row["boundaryTies"]
        records = [item["record"] for item in retrieved]
        pool = [r["foodCd"] for r in records]
        all_codes = pool + [item["record"]["foodCd"] for item in boundary]
        if len(set(all_codes)) != len(all_codes) or len(records) > ranking["k"]:
            raise ValueError(f"Invalid candidate pool for {target['foodCd']}")
        for item in retrieved + boundary:
            verify_record(item["record"], originals, raw=True)
        decision = decide(target, records, boundary_ties=len(boundary))
        original_counts[decision["verdict"]] += 1
        initial, initial_reason = decision["verdict"], decision["reason"]
        assessments = {a["foodCd"]: a for a in decision["assessments"]}
        if (set(pool) != set(assessments) or len(decision["assessments"]) != len(pool)
                or decision["targetCd"] != target["foodCd"]):
            raise ValueError(f"Incomplete candidate assessment: {target['foodCd']}")
        source = None
        if not boundary and initial == "보류":
            documented = documented_reference(target, records, sources)
            if documented:
                raw, source, reason = documented
                if assessments[raw["foodCd"]]["flag"] != "conflict":
                    decision.update(selectedCd=raw["foodCd"], candidateQuote=raw["foodNm"], verdict="참고 비교", reason=reason)
                    assessments[raw["foodCd"]].update(flag="reference", reason=reason)
                else:
                    source = None
        selected = decision["selectedCd"]
        if ((decision["verdict"] == "보류") != (selected is None)
                or (selected is not None and selected not in pool)):
            raise ValueError(f"Invalid candidate selection: {target['foodCd']}")
        candidates = [{**item, "assessment": assessments[item["record"]["foodCd"]]["flag"],
                       "reason": assessments[item["record"]["foodCd"]]["reason"]} for item in retrieved]
        verdict_counts[decision["verdict"]] += 1
        assessment_counts.update(c["assessment"] for c in candidates)
        results.append({**row, "candidates": candidates, "boundaryTies": len(boundary),
                        "sourceRecordVerdict": initial, "sourceRecordReason": initial_reason, "evidenceSource": source,
                        "boundaryTieCodes": all_codes[len(pool):],
                        **{k: v for k, v in decision.items() if k != "assessments"}})

    summary = {"verdicts": {v: verdict_counts[v] for v in ("직접 비교", "참고 비교", "보류")},
               "nameOnlyVerdicts": {v: original_counts[v] for v in ("직접 비교", "참고 비교", "보류")},
               "documentedReferences": sum(r["evidenceSource"] is not None for r in results),
               "candidateFlags": dict(sorted(assessment_counts.items())),
               "candidateLinks": sum(assessment_counts.values()),
               "queriesWithoutSameLv4InTop5": sum(not any(c["record"]["lv4Cd"] == r["target"]["lv4Cd"]
                                                          for c in r["candidates"]) for r in results),
               "queriesWithExtraBoundaryTies": sum(bool(r["boundaryTies"]) for r in results)}
    return {**ranking, "policyVersion": "development-source-conditions-v1",
            "status": "unreviewed_proposals", "summary": summary, "results": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("retrieved", "snapshot", "split", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--process-evidence", type=Path, help="Optional locally stored, sourced definitions of processed ingredients.")
    args = parser.parse_args()
    if args.output.resolve() in {p.resolve() for p in (args.retrieved, args.snapshot, args.split, args.process_evidence) if p}:
        parser.error("The report must be distinct from its inputs.")
    sources = read_json(args.process_evidence)["sources"] if args.process_evidence else []
    report = assess(read_json(args.retrieved), read_json(args.split), read_json(args.snapshot), sources)
    save_report(args.output, report)
    print(report["summary"])


if __name__ == "__main__":
    try:
        main()
    except (KeyError, OSError, TypeError, ValueError) as exc:
        sys.exit(f"Development comparison failed: {exc}")
