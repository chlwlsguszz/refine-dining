"""Audit the baseline holds and derive limited judgments from unranked original records."""

import argparse
from collections import Counter, defaultdict
from pathlib import Path

from match import read_json, save_report
from week1_cohort import FIELDS
from week1_snapshot import validate_snapshot


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET = ROOT / "datasets" / "week1" / "2026-11-10"
SCOPE_FIELDS = {"families": "lv4Nm", "processed": "lv5Nm", "states": "lv7Nm"}
RECORD_FIELDS = ("foodCd", "foodNm", "srcCd", "basis", "lv4Nm", "lv5Nm", "lv6Nm",
                 "lv7Nm", "imported", "country", "region", "month")


def in_scope(target, passage):
    return all(not passage["scope"][key] or target[field] in passage["scope"][key]
               for key, field in SCOPE_FIELDS.items())


def index_notes(notes):
    by_code = {}
    for group in notes["groups"]:
        reasons = [group["primary"], *group["secondary"]]
        if len(set(reasons)) != len(reasons) or not set(reasons) <= notes["reasonLabels"].keys():
            raise ValueError(f"Unknown or repeated reason in {reasons}")
        for code in group["targetCodes"]:
            if code in by_code:
                raise ValueError(f"Multiple primary notes for {code}")
            by_code[code] = {k: group[k] for k in ("primary", "secondary", "needed")}
    return by_code


def record_view(record):
    return {key: record[key] for key in RECORD_FIELDS}


def records_from_snapshot(snapshot):
    return {row["food_cd"]: {key: row[col] for key, col in FIELDS.items()} for row in snapshot["rows"]}


def raw_families(records):
    families = defaultdict(list)
    for record in records.values():
        if record["lv7Cd"] == "01":
            families[record["srcCd"], record["lv4Cd"]].append(record)
    return families


def audit_holds(ranking, dataset_id, dev_codes, by_code, families, records, passages):
    if ranking["snapshotId"] != dataset_id:
        raise ValueError("Baseline was produced from a different snapshot")
    codes = [r["target"]["foodCd"] for r in ranking["results"]]
    if len(codes) != len(dev_codes) or set(codes) != dev_codes:
        raise ValueError("Baseline must cover the exact development cohort")
    holds = [r for r in ranking["results"] if r["verdict"] == "보류"]
    if set(by_code) != {r["targetCd"] for r in holds}:
        raise ValueError("Baseline hold coverage differs from the evidence notes")
    rows = []
    for case in holds:
        code = case["targetCd"]
        target = records[code]
        if target["foodNm"] != case["targetQuote"]:
            raise ValueError(f"Incorrect baseline quote for {code}")
        candidates = []
        for candidate in case["candidates"]:
            row = records[candidate["record"]["foodCd"]]
            if (row["lv7Cd"] != "01" or record_view(row) != record_view(candidate["record"])):
                raise ValueError(f"Candidate record has drifted for {code}")
            candidates.append({"rank": candidate["rank"], **record_view(row)})
        same_family = families[target["srcCd"], target["lv4Cd"]]
        family_codes = {r["foodCd"] for r in same_family}
        candidates_in_family = [r for r in candidates if r["foodCd"] in family_codes]
        note = by_code[code]
        if (note["primary"] == "retrieval") != (len(candidates_in_family) == 0):
            raise ValueError(f"Search diagnosis disagrees with baseline for {code}")
        rows.append({"target": record_view(target), **note, "candidates": candidates,
                     "sameSourceFamilyInTop5": len(candidates_in_family),
                     "sameSourceFamilyInCorpus": len(same_family),
                     "applicablePassageIds": [p["id"] for p in passages if in_scope(target, p)],
                     "status": "unjudged_comparison"})
    return rows


def clear_exclusion(target, raw):
    # These exclusions use independently readable source fields. Whole/part overlaps
    # and finer cuts of a broader part are deliberately left unjudged.
    if {str(target["basis"]).lower(), str(raw["basis"]).lower()} == {"100g", "100ml"}:
        return "basis", [target["basis"], raw["basis"]]
    if target["lv5Nm"] != raw["lv5Nm"]:
        return None
    left, right = target["lv6Nm"], raw["lv6Nm"]
    for disjoint in ({"알", "육", "간"}, {"잎", "뿌리", "줄기"}):
        if left != right and {left, right} <= disjoint:
            return "part", [left, right]
    return None


def documented_ingredient(target, raw, passage):
    if passage["use"] != "ingredient_reference" or not in_scope(target, passage):
        return False
    ingredient = passage["rawIngredient"]
    fields = ("srcCd", "basis", "country", "imported", "region", "month")
    return (target["foodNm"].split("_") == [target["lv4Nm"], target["lv5Nm"], target["lv7Nm"]]
            and raw["foodNm"].split("_") == [target["lv4Nm"], ingredient, "생것"]
            and raw["lv5Nm"] == ingredient and raw["lv7Cd"] == "01"
            and all(target[key] == raw[key] for key in fields))


def source_checks(dev_codes, families, records, passages):
    """List exact field exclusions and source-supported ingredients without opening ranked proposals."""
    rows = []
    for code in sorted(dev_codes):
        target = records[code]
        supported, exclusions = [], []
        for raw in sorted(families[target["srcCd"], target["lv4Cd"]], key=lambda row: row["foodCd"]):
            excluded = clear_exclusion(target, raw)
            if excluded:
                exclusions.append({"foodCd": raw["foodCd"], "foodNm": raw["foodNm"],
                                   "field": excluded[0], "sourceValues": excluded[1]})
                continue
            proof = [p["id"] for p in passages if documented_ingredient(target, raw, p)]
            if proof:
                supported.append({"foodCd": raw["foodCd"], "foodNm": raw["foodNm"], "passageIds": proof})
        rows.append({"targetCd": code, "targetQuote": target["foodNm"], "referenceCandidates": supported,
                     "excludedForEqualBasisComparison": exclusions,
                     "status": "documented_reference" if supported else "unjudged"})
    return {"method": "개발 목표 코드와 순위 없는 원본 전체에서 동일 출처·대표식품의 생것을 대조했다. "
            "기준량·명시 부위 충돌과 가공 문단에 명시된 원료만 기록한다. 빈 후보 목록은 전체 후보 부재를 뜻하지 않는다.",
            "humanReviewed": False, "rows": rows}


def build(dataset):
    snapshot = read_json(dataset / "raw-snapshot.json")
    validate_snapshot(snapshot)
    split = read_json(dataset / "review" / "split-manifest.json")
    if snapshot["snapshotId"] != split["snapshotId"]:
        raise ValueError("Development manifest differs from snapshot")
    dev_codes = {r["targetCd"] for r in split["rows"] if r["split"] in {"dev_review", "dev_remaining"}}
    evidence = dataset / "evidence"
    documents = read_json(evidence / "passages.json")
    passages = documents["passages"]
    if len({p["id"] for p in passages}) != len(passages):
        raise ValueError("Duplicate passage IDs")
    records = records_from_snapshot(snapshot)
    families = raw_families(records)
    judgments = source_checks(dev_codes, families, records, passages)
    notes = read_json(evidence / "hold-notes.json")
    ranking = read_json(dataset / "dev-matching" / "proposals.json")
    rows = audit_holds(ranking, snapshot["snapshotId"], dev_codes, index_notes(notes),
                       families, records, passages)
    counts = Counter(r["primary"] for r in rows)
    summary = {"heldCount": len(rows), "primaryCounts": dict(sorted(counts.items())),
               "holdsWithProcessPassages": sum(bool(r["applicablePassageIds"]) for r in rows),
               "developmentTargetsWithDocumentedReference": sum(bool(r["referenceCandidates"]) for r in judgments["rows"]),
               "explicitNegativePairs": sum(len(r["excludedForEqualBasisComparison"]) for r in judgments["rows"]),
               "humanReviewedTargets": 0}
    return {"snapshotId": snapshot["snapshotId"], "evidenceVersion": documents["version"],
            "notesVersion": notes["version"], "baselineProtocol": ranking["protocol"],
            "reasonLabels": notes["reasonLabels"], "summary": summary,
            "sourceOnlyChecks": judgments, "rows": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    args = parser.parse_args()
    report = build(args.dataset)
    save_report(args.dataset / "evidence" / "hold-audit.json", report)
    print(report["summary"])
