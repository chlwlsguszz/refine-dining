"""Freeze a consistent, UTF-8 JSON copy of the current raw_food_materials DB table."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


VERSION = 1
TABLE = "raw_food_materials"
SQL = """
SET SESSION group_concat_max_len = 1048576;
SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;
START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY;
SELECT JSON_OBJECT('rowCount', COUNT(*),
                   'capturedAt', DATE_FORMAT(UTC_TIMESTAMP(6), '%Y-%m-%dT%H:%i:%s.%fZ'))
FROM raw_food_materials;
SELECT ENGINE FROM information_schema.tables
WHERE table_schema = DATABASE() AND table_name = 'raw_food_materials';
SELECT CONCAT('[', GROUP_CONCAT(JSON_OBJECT('name', column_name, 'type', column_type,
                                            'nullable', is_nullable)
                                ORDER BY ordinal_position SEPARATOR ','), ']')
FROM information_schema.columns
WHERE table_schema = DATABASE() AND table_name = 'raw_food_materials';
SELECT GROUP_CONCAT(
           CONCAT('CONVERT(0x', HEX(column_name), ' USING utf8mb4), ',
                  CHAR(96), REPLACE(column_name, CHAR(96), REPEAT(CHAR(96), 2)), CHAR(96))
           ORDER BY ordinal_position SEPARATOR ',')
INTO @members FROM information_schema.columns
WHERE table_schema = DATABASE() AND table_name = 'raw_food_materials';
SET @statement = CONCAT('SELECT JSON_OBJECT(', @members,
                        ') FROM raw_food_materials ORDER BY BINARY food_cd');
PREPARE snapshot_export FROM @statement;
EXECUTE snapshot_export;
DEALLOCATE PREPARE snapshot_export;
COMMIT;
"""


def capture_snapshot():
    mysql = ('MYSQL_PWD="$MYSQL_PASSWORD" exec mysql --default-character-set=utf8mb4 '
             '--batch --raw --skip-column-names --user="$MYSQL_USER" "$MYSQL_DATABASE"')
    command = ["docker", "compose", "exec", "-T", "mysql", "sh", "-c", mysql]
    result = subprocess.run(command, cwd=Path(__file__).resolve().parents[3],
                            input=SQL.encode("utf-8"), stdout=subprocess.PIPE,
                            check=True, timeout=180)
    lines = result.stdout.split(b"\n")
    if len(lines) < 3 or lines[1].strip() != b"InnoDB":
        raise ValueError("A consistent snapshot requires the raw_food_materials InnoDB table.")
    header = json.loads(lines[0])
    schema = json.loads(lines[2])
    for column in schema:
        column["nullable"] = column["nullable"] == "YES"
    rows = [json.loads(line) for line in lines[3:] if line.strip()]
    snapshot = {
        "datasetVersion": VERSION,
        "source": TABLE,
        "sourceDescription": "수집 후 MySQL에 저장된 원본 테이블. 누락값의 0 변환 등 기존 적재 결과를 포함합니다.",
        "capturedAt": header["capturedAt"],
        "rowCount": header["rowCount"],
        "schema": schema,
        "rows": rows,
    }
    snapshot["snapshotId"] = content_id(schema, rows)
    validate_snapshot(snapshot)
    return snapshot


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def content_id(schema, rows):
    """Hash a versioned schema followed by newline-delimited rows in ascending food_cd order."""
    digest = hashlib.sha256(canonical({"datasetVersion": VERSION, "source": TABLE, "schema": schema}))
    for row in rows:
        digest.update(b"\n")
        digest.update(canonical(row))
    return "sha256:" + digest.hexdigest()


def validate_snapshot(snapshot):
    if snapshot["datasetVersion"] != VERSION or snapshot["source"] != TABLE:
        raise ValueError("Unsupported snapshot version or table.")
    schema, rows = snapshot["schema"], snapshot["rows"]
    columns = {column["name"] for column in schema}
    if "food_cd" not in columns or len(columns) != len(schema):
        raise ValueError("Snapshot schema requires unique column names and food_cd.")
    if len(rows) != snapshot["rowCount"]:
        raise ValueError("Snapshot row count differs from the count in the read transaction.")
    previous = None
    for row in rows:
        code = row["food_cd"]
        if set(row) != columns or not isinstance(code, str) or not code.strip():
            raise ValueError(f"Incomplete snapshot row: {code!r}")
        if previous is not None and code <= previous:
            raise ValueError(f"Repeated or out-of-order food_cd: {code!r}")
        previous = code
    if content_id(schema, rows) != snapshot["snapshotId"]:
        raise ValueError("Snapshot digest does not match its schema and rows.")


def publish(output, snapshot):
    """Publish atomically without replacing an existing snapshot, including concurrent writers."""
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(dir=output.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as temporary:
            json.dump(snapshot, temporary, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":"))
            temporary.write("\n")
        try:
            os.link(temporary_name, output)
        except FileExistsError:
            existing = json.loads(output.read_text(encoding="utf-8"))
            validate_snapshot(existing)
            if existing["snapshotId"] != snapshot["snapshotId"]:
                raise ValueError(f"A different snapshot exists at {output}. Choose a fresh path.")
    finally:
        os.unlink(temporary_name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    snapshot = capture_snapshot()
    publish(args.output, snapshot)
    print(f"{snapshot['rowCount']} rows, {len(snapshot['schema'])} columns, {snapshot['snapshotId']}")


if __name__ == "__main__":
    try:
        main()
    except (KeyError, OSError, TypeError, ValueError, subprocess.SubprocessError) as exc:
        sys.exit(f"Snapshot export failed: {exc}")
