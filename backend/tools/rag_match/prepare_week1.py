"""Prepare the first independent review set from an immutable MySQL snapshot."""

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
import sys
import tempfile

from week1_cohort import build_packet
from week1_review import render_review_page
from week1_snapshot import validate_snapshot


PRIOR_STRATA = {
    "같은 출처·중분류의 다른 소분류에 생것 존재": "same_lv5",
    "같은 출처·대표식품의 다른 중분류에 생것 존재": "lv4_only",
}
ROLES = {"dev_review": "개발 · 이번 검수", "dev_remaining": "개발 · 나머지", "test": "최종 평가"}
CSV_COLUMNS = {
    "분할": "split", "식품군": "family", "대표식품코드": "lv4Cd", "대표식품명": "lv4Nm",
    "중분류명": "lv5Nm", "소분류명": "lv6Nm", "대상 식품코드": "targetCd", "대상 식품명 원문": "targetNm",
    "출처": "srcNm", "영양 기준량": "basis", "후보 탐색 범위": "stratum",
    "동일 출처·대표식품 생것 후보 수": "candidateCount", "그중 같은 중분류 후보 수": "sameLv5CandidateCount",
}


def check_prior(manifest, previous_csv):
    expected = {}
    with previous_csv.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            stratum = PRIOR_STRATA.get(row["검토 근거"])
            if row["검토 구분"] == "RAG 매칭 검토" and stratum:
                code = row["식품코드"]
                if code in expected:
                    raise ValueError(f"Duplicate target in previous audit: {code}")
                expected[code] = stratum
    current = {row["targetCd"]: row["stratumId"] for row in manifest["rows"]}
    mismatch = sorted(code for code in expected.keys() | current.keys() if expected.get(code) != current.get(code))
    if not expected or mismatch:
        raise ValueError(f"Previous audit differs in target membership or stratum: {mismatch[:12]}")
    return {"fileName": previous_csv.name, "sha256": hashlib.sha256(previous_csv.read_bytes()).hexdigest(),
            "matchedTargetsAndStrata": len(current)}


def write_split_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as target:
        writer = csv.writer(target)
        writer.writerow(CSV_COLUMNS)
        for row in sorted(rows, key=lambda x: (x["family"], x["targetCd"])):
            writer.writerow(ROLES[row[key]] if key == "split" else row[key] for key in CSV_COLUMNS.values())


def prepare(snapshot_path, output_dir, seed, previous_csv=None):
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    validate_snapshot(snapshot)
    manifest, packet = build_packet(snapshot["rows"], snapshot["snapshotId"], seed=seed)
    manifest["packetId"] = packet["packetId"]
    manifest["sourceRowCount"] = snapshot["rowCount"]
    manifest["rawCandidateCount"] = len(packet["catalog"])
    manifest["familyCount"] = len({r["familyCode"] for r in manifest["rows"]})
    if previous_csv:
        manifest["priorAuditCheck"] = check_prior(manifest, previous_csv)

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output_dir.parent) as stage:
        prepared = Path(stage) / "review"
        prepared.mkdir()
        (prepared / "split-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_split_csv(prepared / "food-groups.csv", manifest["rows"])
        (prepared / "dev20-review.html").write_text(render_review_page(packet), encoding="utf-8")
        if output_dir.exists():
            for file in prepared.iterdir():
                other = output_dir / file.name
                if not other.is_file() or other.read_bytes() != file.read_bytes():
                    raise ValueError(f"Existing review differs at {other}; choose a new output directory.")
        else:
            prepared.rename(output_dir)

    return {"snapshotId": snapshot["snapshotId"], "packetId": packet["packetId"],
            "targets": len(manifest["rows"]), "rawCandidates": len(packet["catalog"]),
            "roles": dict(Counter(row["split"] for row in manifest["rows"])),
            "strata": dict(Counter(row["stratumId"] for row in manifest["rows"])),
            "priorAuditCheck": manifest.get("priorAuditCheck"), "review": str(output_dir / "dev20-review.html")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20261110)
    parser.add_argument("--previous-csv", type=Path, help="Check cohort membership against the earlier exclusion audit.")
    args = parser.parse_args()
    print(json.dumps(prepare(args.snapshot, args.output_dir, args.seed, args.previous_csv), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (KeyError, OSError, TypeError, ValueError) as error:
        sys.exit(f"Review preparation failed: {error}")
