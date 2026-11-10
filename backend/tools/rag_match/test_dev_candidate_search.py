import unittest

try:
    import numpy as np
except ImportError:
    np = None

if np is not None:
    from dev_candidate_search import development_rows, top_candidates


@unittest.skipIf(np is None, "NumPy is required for development retrieval.")
class DevelopmentRetrievalTests(unittest.TestCase):
    def test_only_dev_queries_are_returned_and_family_overlap_is_rejected(self):
        rows = [{"food_cd": c, "food_nm": c, "food_lv7cd": "50"} for c in "ABC"]
        entries = [{"targetCd": c, "targetNm": c, "familyCode": c, "split": scope}
                   for c, scope in zip("ABC", ["dev_remaining", "test", "dev_review"])]
        snap = {"snapshotId": "frozen", "rows": rows}
        manifest = {"snapshotId": "frozen", "totalTargets": 3,
                    "splitCounts": {"dev_review": 1, "dev_remaining": 1, "test": 1}, "rows": entries}
        self.assertEqual([r["food_cd"] for _, r in development_rows(snap, manifest)], ["A", "C"])
        entries[1]["familyCode"] = "C"
        with self.assertRaisesRegex(ValueError, "family"):
            development_rows(snap, manifest)

    def test_cutoff_ties_are_preserved_independently_of_catalog_order(self):
        raw = [{"food_cd": c, "food_nm": f"{c}_생것"} for c in "DACB"]
        scores = [.7, .7, .95, .7]
        lexical = [0., 3., 2., 1.]
        top, ties = top_candidates(scores, lexical, raw, k=2)
        self.assertEqual([c["record"]["foodCd"] for c in top], ["C", "A"])
        self.assertEqual([c["record"]["foodCd"] for c in ties], ["B", "D"])
        self.assertEqual((top[1]["rank"], top[1]["rankWorst"]), (2, 4))
        self.assertEqual(top_candidates(scores[::-1], lexical[::-1], raw[::-1], 2), (top, ties))
        self.assertIsNone(ties[-1]["lexicalRank"])
