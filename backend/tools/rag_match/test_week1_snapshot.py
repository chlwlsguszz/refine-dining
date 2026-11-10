import json
from pathlib import Path
import tempfile
import unittest

from week1_snapshot import TABLE, VERSION, content_id, publish, validate_snapshot


def snapshot(value=None, timestamp="2026-11-10T00:00:00.000000Z"):
    schema = [{"name": "food_cd", "type": "varchar(50)", "nullable": False},
              {"name": "prot", "type": "double", "nullable": True}]
    rows = [{"food_cd": "식품01", "prot": value}]
    return {"datasetVersion": VERSION, "source": TABLE, "schema": schema, "rows": rows,
            "capturedAt": timestamp, "rowCount": len(rows), "snapshotId": content_id(schema, rows)}


class SnapshotTests(unittest.TestCase):
    def test_detects_changed_cells_and_duplicate_or_incomplete_rows(self):
        for change in ("cell", "missing", "duplicate"):
            with self.subTest(change=change):
                data = snapshot()
                if change == "cell":
                    data["rows"][0]["prot"] = 0.0
                elif change == "missing":
                    del data["rows"][0]["prot"]
                else:
                    data["rows"].append(data["rows"][0].copy())
                    data["rowCount"] += 1
                with self.assertRaises(ValueError):
                    validate_snapshot(data)

    def test_matching_export_keeps_original_capture_and_different_export_cannot_replace_it(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "snapshot.json"
            initial = snapshot()
            publish(output, initial)
            publish(output, snapshot(timestamp="2026-11-11T00:00:00.000000Z"))
            with self.assertRaisesRegex(ValueError, "different snapshot"):
                publish(output, snapshot(0.0))
            self.assertEqual(initial, json.loads(output.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
