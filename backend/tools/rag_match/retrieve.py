"""Export eligible cooked foods and their same-source raw candidates from MySQL."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def retrieve_pairs():
    root = Path(__file__).resolve().parents[3]
    sql = Path(__file__).with_suffix(".sql").read_bytes()
    mysql = (
        'MYSQL_PWD="$MYSQL_PASSWORD" exec mysql --default-character-set=utf8mb4 '
        '--batch --raw --skip-column-names --user="$MYSQL_USER" "$MYSQL_DATABASE"'
    )
    # The shell expands credentials inside the existing container only.
    command = ["docker", "compose", "exec", "-T", "mysql", "sh", "-c", mysql]
    result = subprocess.run(command, cwd=root, input=sql, stdout=subprocess.PIPE,
                            check=True, timeout=120)
    return [json.loads(line) for line in result.stdout.decode("utf-8").splitlines()]


def group_by_target(pairs):
    groups = {}
    for pair in pairs:
        target = pair["target"]
        group = groups.setdefault(target["foodCd"], {"target": target, "candidates": []})
        group["candidates"].append(pair["candidate"])
    return list(groups.values())


def save_snapshot(output, groups):
    output.parent.mkdir(parents=True, exist_ok=True)
    # Leave an earlier complete export intact if writing this snapshot fails.
    temporary = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=output.parent, delete=False
    )
    try:
        with temporary:
            json.dump(groups, temporary, ensure_ascii=False, indent=2)
            temporary.write("\n")
        os.replace(temporary.name, output)
    finally:
        Path(temporary.name).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    groups = group_by_target(retrieve_pairs())
    save_snapshot(args.output, groups)
    print(f"Exported {len(groups)} targets and "
          f"{sum(len(group['candidates']) for group in groups)} candidate links.")


if __name__ == "__main__":
    try:
        main()
    except (subprocess.SubprocessError, OSError, ValueError) as error:
        sys.exit(f"Retrieval failed: {error}")
