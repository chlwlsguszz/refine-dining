import unittest

from blind_retrieval import NameSearch


class BlindRetrievalTests(unittest.TestCase):
    def test_duplicate_names_tie_and_order_only_changes_output_positions(self):
        names = ["참다랑어_육_생것", "참다랑어_육_생것", "대구_간_생것"]
        original = NameSearch(names).scores("참다랑어_육_구운것")
        self.assertGreater(original[0], original[2])
        self.assertEqual(original[0], original[1])
        self.assertEqual(NameSearch(names[::-1]).scores("참다랑어_육_구운것"), original[::-1])

    def test_korean_compound_tokens_can_retrieve_a_partial_name(self):
        scores = NameSearch(["율무가루", "참다랑어_육"]).scores("율무")
        self.assertGreater(scores[0], 0)
        self.assertEqual(scores[1], 0)

    def test_no_shared_text_does_not_return_a_guess(self):
        self.assertEqual(NameSearch(["밀", "대구"]).scores("참치"), [0.0, 0.0])
        self.assertEqual(NameSearch(["", "   "]).scores("호밀"), [0.0, 0.0])
        self.assertEqual(NameSearch([]).scores("호밀"), [])

    def test_no_metadata_or_target_state_inference(self):
        with self.assertRaises(TypeError):
            NameSearch([{"foodNm": "오미자", "foodLv6Cd": "secret"}])
        scores = NameSearch(["사과_구운것", "사과_생것"]).scores("사과_구운것")
        self.assertGreater(scores[0], scores[1])


if __name__ == "__main__":
    unittest.main()
