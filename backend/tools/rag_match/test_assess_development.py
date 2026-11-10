import unittest

from assess_development import documented_reference


class DocumentedReferenceTests(unittest.TestCase):
    def setUp(self):
        self.source = {"family": "인삼", "processed": "홍삼", "state": "말린것", "rawIngredient": "수삼",
                       "summary": "홍삼의 원료는 수삼입니다."}
        self.target = {"foodNm": "인삼_홍삼_말린것", "lv4Nm": "인삼", "lv5Nm": "홍삼", "lv7Nm": "말린것",
                       "basis": "100g", "srcCd": "1", "country": "해당없음", "imported": "N", "region": "", "month": ""}
        self.raw = dict(self.target, foodNm="인삼_수삼_생것", lv5Nm="수삼", lv7Cd="01", lv7Nm="생것")

    def test_applies_only_to_the_named_ingredient_and_state(self):
        result = documented_reference(self.target, [self.raw], [self.source])
        self.assertIs(result[0], self.raw)
        self.assertIs(result[1], self.source)
        extract = dict(self.target, foodNm="인삼_홍삼_추출", lv7Nm="추출", basis="100ml")
        self.assertIsNone(documented_reference(extract, [self.raw], [self.source]))
        self.assertIsNone(documented_reference(self.target, [dict(self.raw, lv4Nm="산삼")], [self.source]))

    def test_same_ingredient_does_not_override_scope_or_ambiguity(self):
        for modification in ({"basis": "100ml"}, {"country": "중국", "imported": "Y"}, {"srcCd": "3"}):
            with self.subTest(modification=modification):
                self.assertIsNone(documented_reference(self.target, [dict(self.raw, **modification)], [self.source]))
        self.assertIsNone(documented_reference(self.target, [self.raw, self.raw.copy()], [self.source]))
        self.assertIsNone(documented_reference(dict(self.target, imported="Y"), [dict(self.raw, imported="Y")], [self.source]))
