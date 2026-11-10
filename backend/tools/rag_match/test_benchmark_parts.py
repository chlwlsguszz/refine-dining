import unittest

from benchmark_parts import check_parts, run_part_checks


class ExplicitPartTests(unittest.TestCase):
    def test_clear_conflict_and_same_part_without_processing_or_identifier_fields(self):
        self.assertEqual(check_parts("식품_육_삶은것", "식품_간_생것")[0], "conflict")
        self.assertEqual(check_parts("식품_잎_말린것", "식품_잎_생것")[0], "same_part")
        self.assertEqual(check_parts("식품_설도_구운것", "식품_목심(목심살)_생것")[0], "conflict")

    def test_incomplete_overlapping_and_nested_parts_do_not_become_definite_mismatches(self):
        for left, right in (("전체", "육"), ("간", "내장"), ("육(뱃살)", "육"), ("분말", "뿌리"), ("뿌리_잎", "잎")):
            with self.subTest(left=left, right=right):
                self.assertEqual(check_parts(f"식품_{left}_가공품", f"식품_{right}_생것")[0], "review")

    def test_missing_curated_observation_cannot_be_silently_omitted(self):
        with self.assertRaisesRegex(ValueError, "missing or has changed"):
            run_part_checks([])


if __name__ == "__main__":
    unittest.main()
