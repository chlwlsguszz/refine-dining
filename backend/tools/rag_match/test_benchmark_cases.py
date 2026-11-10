import unittest

from benchmark_cases import build_reference_pairs


def record(code, state_code, state, name, **changes):
    row = {
        "food_cd": code, "food_lv7cd": state_code, "food_lv7nm": state, "food_nm": name,
        "src_cd": "1", "src_nm": "출처", "food_lv4cd": "04", "food_lv4nm": "식품",
        "food_lv5cd": "050", "food_lv6cd": "0060", "nut_con_srtr_qua": "100g",
        "coo_cd": "", "coo_nm": "해당없음", "impt_yn": "N", "food_coo_rgn_nm": "",
        "prd_coll_cap_mon": "", "crtr_ymd": "2025-12-23",
    }
    return dict(row, **changes)


class ReferencePairTests(unittest.TestCase):
    def setUp(self):
        self.raw = record("raw", "01", "생것", "식품_생것")
        self.dried = record("dried", "02", "말린것", "식품_말린것")

    def test_explicit_single_state_and_uniqueness(self):
        steamed = record("steamed", "49", "찐것", "식품_찐것")
        pairs = build_reference_pairs([steamed, self.raw, self.dried])
        self.assertEqual([(p["targetCd"], p["rawCd"]) for p in pairs], [("dried", "raw"), ("steamed", "raw")])
        self.assertFalse(pairs[0]["originRecorded"])
        self.assertEqual(build_reference_pairs([self.dried, self.raw, dict(self.raw, food_cd="other")]), [])

    def test_name_scope_metadata_and_unknown_origin_do_not_create_matches(self):
        for change in (
                {"food_nm": "식품_잎_말린것"}, {"food_nm": "식품_말린것_완도_평균"},
                {"food_nm": "식품_말린것_말린것"}, {"nut_con_srtr_qua": "100ml"},
                {"src_cd": "3"}, {"food_lv6cd": "0061"}, {"coo_nm": "대한민국"},
                {"food_coo_rgn_nm": "완도"}, {"prd_coll_cap_mon": "05"}):
            with self.subTest(change=change):
                self.assertEqual(build_reference_pairs([self.raw, dict(self.dried, **change)]), [])
        imported = [dict(row, impt_yn="Y") for row in (self.raw, self.dried)]
        self.assertEqual(build_reference_pairs(imported), [])

    def test_multi_step_or_unknown_process_cannot_supply_a_positive_reference(self):
        for code, state in (("83", "말린것을 삶은것"), ("00", "해당없음"), ("99", "조리예에 따라 조리한것")):
            with self.subTest(code=code):
                food = record("processed", code, state, f"식품_{state}")
                self.assertEqual(build_reference_pairs([self.raw, food]), [])


if __name__ == "__main__":
    unittest.main()
