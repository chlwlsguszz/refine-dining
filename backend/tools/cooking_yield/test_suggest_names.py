import unittest

import numpy as np

from suggest_names import CutNames


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


if __name__ == "__main__":
    unittest.main()
