import unittest

from run_name_benchmark import rank_bounds, split_references


class NameBenchmarkTests(unittest.TestCase):
    def test_ties_span_the_cutoff_and_zero_is_not_a_candidate(self):
        scores = [8.0, 7.0, 6.0, 4.0, 3.0, 3.0 + 1e-13, 0.0]
        self.assertEqual(rank_bounds(scores, 0), (1, 1))
        self.assertEqual(rank_bounds(scores, 4), (5, 6))
        self.assertEqual(rank_bounds(scores, 6), (None, None))

    def test_holdout_keeps_alias_codes_of_the_same_official_food_together(self):
        manifest = [{"targetCd": "unresolved", "lv4Cd": "A", "split": "test"}]
        by_code = {"unresolved": {"food_lv4cd": "A", "food_lv4nm": "메밀 국수"},
                   "easy": {"food_lv4cd": "B", "food_lv4nm": "메밀국수"},
                   "other": {"food_lv4cd": "C", "food_lv4nm": "오미자"}}
        pairs = [{"targetCd": "easy", "familyCode": "B"}, {"targetCd": "other", "familyCode": "C"}]
        kept, excluded, _, _ = split_references(pairs, manifest, by_code)
        self.assertEqual(kept, [pairs[1]])
        self.assertEqual(excluded, 1)
