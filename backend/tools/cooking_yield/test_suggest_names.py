import unittest

import numpy as np

from suggest_names import CutNames, YieldSearch
from import_usda import WORKBOOK, build_catalog


class AdversarialEncoder:
    """Score breast above thigh so the test exercises the cut constraint, not a lucky rank."""
    def encode(self, texts, batch_size):
        if len(texts) == 1:
            return np.array([[1., 0.]])
        return np.array([[1., 0.] if "가슴" in text else [.85, .527] for text in texts])


class YieldNameTests(unittest.TestCase):
    def test_only_compatible_terms_can_be_suggested(self):
        breast = "닭 가슴 (껍질 포함)"
        thigh = "닭 넓적다리 (껍질 포함)"
        index = CutNames({"records": [{"foodLabel": label, "foodAliases": []} for label in [breast, thigh]]},
                         AdversarialEncoder())
        self.assertEqual([thigh], index.suggest("닭 허벅지", {breast, thigh}))
        for name in ("껍질 벗긴 닭 허벅지", "닭 심장", "옥수수", "소고기 허벅지"):
            self.assertEqual([], index.suggest(name, {breast, thigh}))
        self.assertEqual([], index.suggest("닭 허벅지", {breast}))


class SearchEncoder:
    def __init__(self):
        self.calls = 0

    def encode(self, texts, batch_size):
        self.calls += 1
        if texts[0].startswith("query:"):
            return np.array([[1., 0.]])
        # Wrong species/part deliberately gets the stronger cosine score.
        return np.array([[.89, .456], [.91, .415], [.98, .199]])


def record(code, species, cut, text, method="grill", tags=None):
    return {"id": code, "species": species, "cut": cut, "foodLabel": text, "sourceDescription": text,
            "sourceMethod": "Grilled", "methodLabel": "그릴 구이", "methodKey": method,
            "foodAliases": [], "preparationTags": tags or []}


class YieldSearchTests(unittest.TestCase):
    def setUp(self):
        self.encoder = SearchEncoder()
        self.index = YieldSearch({"records": [
            record("tenderloin", "beef", "tenderloin", "소고기 안심 beef tenderloin"),
            record("loin", "beef", "loin", "소고기 등심 beef loin"),
            record("thigh", "chicken", "thigh", "닭 넓적다리 chicken thigh", "roast", ["skin_on"]),
        ]}, self.encoder)

    def test_known_cut_reranks_nearby_vectors_and_species_does_not_cross(self):
        result = self.index.search("소고기 안심", "구이")
        self.assertEqual(["tenderloin", "loin"], [r["id"] for r in result])
        self.assertLess(result[0]["score"], result[1]["score"])

    def test_condition_conflicts_are_retrieved_for_java_to_explain(self):
        result = self.index.search("껍질 없는 닭 넓적다리", "오븐구이")
        self.assertEqual(["thigh"], [r["id"] for r in result])

    def test_unsupported_food_returns_no_meat_record(self):
        for name in ("감자", "옥수수", "두부", "김치", "연어", "닭고기 감자 볶음"):
            self.assertEqual([], self.index.search(name, "구이"))

    def test_repeated_request_uses_bounded_cache(self):
        self.index.search("소고기 안심", "구이")
        calls = self.encoder.calls
        self.index.search("소고기 안심", "구이")
        self.assertEqual(calls, self.encoder.calls)
        for i in range(130):
            self.index.search("소고기 " + str(i))
        self.assertLessEqual(len(self.index.cache), 128)


class SourceCatalogTests(unittest.TestCase):
    def test_all_source_rows_and_missing_statistics_are_preserved(self):
        catalog = build_catalog(WORKBOOK)
        records = {row["id"]: row for row in catalog["records"]}
        self.assertEqual(173, len(records))
        self.assertEqual(10, sum(row["aggregate"] for row in records.values()))
        self.assertEqual(69, records["usda-r2-05094"]["meanPercent"])
        self.assertIsNone(records["usda-r2-05094"]["sampleCount"])
        self.assertIsNone(records["usda-r2-23345"]["minPercent"])
        self.assertEqual("tenderloin", records["usda-r2-23345"]["cut"])
        self.assertEqual(68, records["usda-r2-17204"]["meanPercent"])
        self.assertEqual(67.64, records["usda-r2-17204"]["maxPercent"])
        self.assertTrue(records["usda-r2-17204"]["statisticNote"])


if __name__ == "__main__":
    unittest.main()
