import unittest

import numpy as np

from retrieval_policy import Index


def food(code, family="wheat", source="1", middle="other"):
    return {"food_cd": code, "src_cd": source, "food_lv4cd": family, "food_lv5cd": middle}


class RetrievalPolicyTest(unittest.TestCase):
    def setUp(self):
        self.raw = [food("a", family="meat"), food("b", family="meat"), food("c", family="rice"),
                    food("d", source="2"), food("e"), food("f", middle="whole"), food("g")]
        self.index = Index(self.raw)
        self.addCleanup(self.index.sql.close)
        self.query = food("query", middle="whole")
        self.scores = np.asarray([.99, .98, .97, .96, .95, .94, .93])

    def test_local_allocation_plus_global_refill(self):
        selected, uncertain, boundary = self.index.search("family3_global", self.query, self.scores)
        self.assertEqual(selected, [3, 4, 5, 0, 1])
        self.assertFalse(uncertain or boundary)
        selected, _, _ = self.index.search("family3_global", food("q", family="rice"), self.scores)
        self.assertEqual(selected, [2, 0, 1, 3, 4])
        selected, _, _ = self.index.search("family3_global", food("q", family="missing"), self.scores)
        self.assertEqual(selected, [0, 1, 2, 3, 4])

    def test_sql_retains_same_source_and_prefers_known_middle(self):
        selected, _, _ = self.index.search("hierarchy_sql", self.query, self.scores)
        self.assertEqual(selected, [5, 4, 6])

    def test_tie_at_reserved_slot_is_disclosed_unless_global_slots_include_it(self):
        self.scores[6] = self.scores[5]
        selected, uncertain, boundary = self.index.search("family3_global", self.query, self.scores)
        self.assertEqual(selected, [3, 4, 5, 0, 1])
        self.assertEqual(boundary, {6})
        self.assertEqual(uncertain, {5})
        self.scores[:3] = .2
        selected, _, boundary = self.index.search("family3_global", self.query, self.scores)
        self.assertIn(6, selected)
        self.assertNotIn(6, boundary)


if __name__ == "__main__":
    unittest.main()
