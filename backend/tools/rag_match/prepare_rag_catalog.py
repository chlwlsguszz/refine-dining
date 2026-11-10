"""Join frozen DB observations to the official public download, keeping missing values explicit."""

import argparse
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
import gzip
import hashlib
import json
from pathlib import Path

from week1_snapshot import canonical, validate_snapshot


ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "datasets/week1/2026-11-10"
SOURCE = "https://www.data.go.kr/data/15100065/standard.do"
NUTRIENTS = "enerc water prot fatce ash chocdf sugar fibtg ca fe p k nat vita_rae retol cartb thia ribf nia vitc vitd chole fasat fatrn".split()


def matches_identity(row, official):
    for key, value in row.items():
        if key == "id" or key in NUTRIENTS:
            continue
        field = key.upper()
        if field.startswith("FOOD_LV"):
            field = field[:-2] + "_" + field[-2:]
        if (value or "") != (official[field] or ""):
            return False
    return True


def cell_state(stored, literal):
    if literal is None or not str(literal).strip() or literal in ("-", "N/A"):
        return "missing" if stored in (None, 0) else "conflict"
    try:
        original = Decimal(str(literal))
        if original.is_finite() and stored is not None and original == Decimal(str(stored)):
            return "observed"
    except InvalidOperation:
        pass
    return "conflict"


def prepare(snapshot, source_rows, source_digest):
    validate_snapshot(snapshot)
    official = defaultdict(list)
    for item in source_rows:
        official[item["FOOD_CD"]].append(item)
    rows, totals = [], Counter()
    for row in snapshot["rows"]:
        matches = [item for item in official[row["food_cd"]] if matches_identity(row, item)]
        cells = {}
        for key in NUTRIENTS:
            literals = {item[key.upper()] for item in matches}
            literal = next(iter(literals)) if len(literals) == 1 else None
            status = cell_state(row[key], literal) if len(literals) == 1 else "unverified"
            totals[status] += 1
            if status == "observed" and row[key] == 0:
                totals["observedZero"] += 1
            cells[key] = {"status": status, "sourceText": literal}
        rows.append({"original": row, "cells": cells})
    version = "sha256:" + hashlib.sha256(canonical([snapshot["snapshotId"], source_digest, rows])).hexdigest()
    return {"version": version, "snapshotId": snapshot["snapshotId"], "sourceUrl": SOURCE,
            "upstreamSha256": source_digest, "upstreamRows": len(source_rows),
            "rowCount": len(rows), "counts": dict(totals), "rows": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DATA / "raw-snapshot.json")
    parser.add_argument("--official", type=Path, default=DATA / "nutrition/official-materials.json.gz")
    parser.add_argument("--output", type=Path, default=ROOT / "backend/build/rag/catalog.json")
    args = parser.parse_args()
    if args.output.resolve() in {args.snapshot.resolve(), args.official.resolve()}:
        parser.error("Choose an output distinct from the source files.")
    packed = args.official.read_bytes()
    report = prepare(json.loads(args.snapshot.read_bytes()), json.loads(gzip.decompress(packed)),
                     hashlib.sha256(packed).hexdigest())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical(report))
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
