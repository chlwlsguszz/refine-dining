import tempfile
from pathlib import Path
import unittest

try:
    import numpy as np
except ImportError:
    np = None

if np is not None:
    from compare_dense import Ranking, compare
from week1_snapshot import content_id


def inputs():
    rows = [{"food_cd": "A", "food_nm": "오미자_생것", "food_lv7cd": "01"},
            {"food_cd": "B", "food_nm": "두부_생것", "food_lv7cd": "01"},
            {"food_cd": "T", "food_nm": "오미자_말린것", "food_lv7cd": "02"}]
    schema = [{"name": k, "type": "varchar", "nullable": False} for k in rows[0]]
    sid = content_id(schema, rows)
    snapshot = {"source": "raw_food_materials", "datasetVersion": 1, "snapshotId": sid,
                "rowCount": 3, "schema": schema, "rows": rows}
    positive = {"targetCd": "T", "targetName": "오미자_말린것", "rawCd": "A",
                "rawName": "오미자_생것", "rankBest": 1, "rankWorst": 1}
    conflict = {**positive, "rawCd": "B", "rawName": "두부_생것",
                "rankBest": None, "rankWorst": None, "expectedStatus": "conflict"}
    baseline = {"snapshotId": sid, "protocol": "name-only-reference-pairs-v1", "splitSeed": 5, "splitProtocol": "test",
                "referenceResults": [positive], "partChecks": {"cases": [conflict], "metrics": {}},
                "summary": {"evaluatedPairs": 1, "rawSearchPool": 2, "hitsAt": {
                    str(k): {"guaranteed": 1, "possibleIncludingTies": 1} for k in (1, 5)}}}
    data = {"snapshot_id": sid, "model": "test-only", "revision": "fixture", "raw_codes": ["B", "A"],
            "query_codes": ["T"], "raw_vectors": [[1., 0.], [0., 7.]], "query_vectors": [[8., 0.]]}
    return snapshot, baseline, data


@unittest.skipIf(np is None, "NumPy is required for the local embedding benchmark.")
class DenseComparisonTests(unittest.TestCase):
    def test_equal_and_near_equal_scores_have_identical_rrf_contributions(self):
        x = Ranking([.91, .87 + 1e-8, .87, 0., -.1], 1e-6)
        self.assertEqual(list(x.first), [1, 2, 2, 0, 0])
        self.assertEqual(list(x.last), [1, 3, 3, 0, 0])
        np.testing.assert_allclose(x.contribution(), [1/61, 1/62.5, 1/62.5, 0, 0])

    def test_round_trip_permuted_corpus_includes_lost_hit_and_fused_tie(self):
        snapshot, baseline, data = inputs()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.npz"
            np.savez(path, **data)
            report = compare(snapshot, baseline, path)
        methods = report["referenceResults"][0]["methods"]
        self.assertEqual(methods["dense"]["firstPlaceCandidates"][0]["foodCd"], "B")
        self.assertIsNone(methods["dense"]["rankWorst"])
        self.assertEqual((methods["hybrid"]["rankBest"], methods["hybrid"]["rankWorst"]), (1, 2))
        self.assertEqual(report["summary"]["changesAgainstLexical"]["hybrid"]["1"]["lost"], ["T"])
        self.assertEqual(report["partChecks"]["conflictPairsInTopKBeforeGuard"]["dense"]["1"], 1)

    def test_invalid_archive_and_changed_baseline_are_rejected(self):
        snapshot, baseline, fixture = inputs()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.npz"
            for invalid in ({"raw_codes": ["A", "A"]}, {"query_codes": ["U"]}, {"snapshot_id": "another"},
                            {"raw_vectors": [[0., 0.], [1., 0.]]}, {"query_vectors": [[np.nan, 1.]]}):
                with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                    np.savez(path, **{**fixture, **invalid})
                    compare(snapshot, baseline, path)
            np.savez(path, **fixture)
            baseline["referenceResults"][0]["rankWorst"] = 2
            with self.assertRaisesRegex(ValueError, "failed to reproduce"):
                compare(snapshot, baseline, path)


if __name__ == "__main__":
    unittest.main()
