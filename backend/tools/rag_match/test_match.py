import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import match


def food(code, state, place, month="평균"):
    return {"foodCd": code, "foodNm": f"매생이_전체_{state}_{place}_{month}", "lv7Nm": state,
            "lv7Cd": "01" if state == "생것" else "02", "srcCd": "2", "lv6Cd": "128250139",
            "country": "대한민국", "imported": "N", "region": place, "month": month, "basis": "100g"}


def case(target_code):
    return {"target": food(target_code, "말린것", "대표"),
            "candidates": [food("A", "생것", "완도"), food("B", "생것", "장흥")]}


def held(row):
    return {"targetCd": row["target"]["foodCd"], "selectedCd": None, "verdict": "보류",
            "reason": "대표 평균 대상에 완도 평균과 장흥 평균이 동일하게 경합한다.",
            "targetQuote": row["target"]["foodNm"], "candidateQuote": None,
            "alternatives": "A 완도와 B 장흥은 모두 지역 평균이어서 우열 근거가 없다."}


class MatchingTest(unittest.TestCase):
    def test_only_retrieved_ids_and_quotes_are_accepted(self):
        item = case("T")
        index = match.evidence_index([item])
        decision = held(item) | {"verdict": "참고 비교", "selectedCd": "A"}
        for changes in ({"selectedCd": "X", "candidateQuote": "완도"},
                        {"candidateQuote": "대표_평균"}, {"targetQuote": "부산_9월"},
                        {"selectedCd": None}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                match.validate_decisions(index, [decision | changes])
        self.assertEqual(match.validate_decisions(index, [held(item)])["T"]["verdict"], "보류")

    def test_direct_comparison_requires_same_observation_scope(self):
        item = case("T")
        decision = held(item) | {"selectedCd": "A", "verdict": "직접 비교",
                                 "candidateQuote": item["candidates"][0]["foodNm"]}
        with self.assertRaisesRegex(ValueError, "direct comparison"):
            match.validate_decisions(match.evidence_index([item]), [decision])
        item["candidates"][0] = food("A", "생것", "대표")
        decision["candidateQuote"] = item["candidates"][0]["foodNm"]
        match.validate_decisions(match.evidence_index([item]), [decision])

    def test_hallucinated_code_in_prose_only_invalidates_affected_row(self):
        left, right = case("T1"), case("T2")
        invalid = held(right) | {"alternatives": "후보 R211-000000000-0000은 지역 평균이다."}
        index = match.evidence_index([left, right])
        with self.assertRaisesRegex(ValueError, "code cited outside"):
            match.validate_decisions(index, [held(left), invalid])
        self.assertEqual(set(match.restore_valid(index, [held(left), invalid])), {"T1"})

    def test_representative_label_does_not_establish_geographic_coverage(self):
        row = case("T")
        inferred = held(row) | {"reason": "대표 표기는 지역 제한이 없는 전국 평균이다."}
        with self.assertRaisesRegex(ValueError, "지리적 범위"):
            match.validate_decisions(match.evidence_index([row]), [inferred])

    def test_selective_review_keeps_other_rows_and_records_actual_model(self):
        rows = [case("T1"), case("T2")]
        notes = {"T2": "두 지역 평균의 원문을 다시 확인한다."}
        with tempfile.TemporaryDirectory() as directory, patch.object(match, "api_key", return_value="test"):
            output = Path(directory) / "review.json"
            with patch.object(match, "generate_batch", return_value=[held(row) for row in rows]):
                match.run(rows, output, "model-a", 2)
            with patch.object(match, "generate_batch", return_value=[held(rows[1])]) as generate:
                match.run(rows, output, "model-a", 2, notes, "model-b")
                self.assertEqual(generate.call_args.args[:2], ([rows[1]], "model-b"))
                self.assertIn(notes["T2"], generate.call_args.args[3])
            saved = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(saved["modelsByTarget"], {"T1": "model-a", "T2": "model-b"})
            self.assertEqual(saved["appliedReviewNotes"], notes)
            with patch.object(match, "generate_batch") as generate:
                match.run(rows, output, "model-a", 2, notes, "model-b")
                generate.assert_not_called()

    def test_resume_checks_evidence_and_preserves_finished_batches(self):
        rows = [case("T1"), case("T2")]
        with tempfile.TemporaryDirectory() as directory, patch.object(match, "api_key", return_value="test"):
            output = Path(directory) / "results.json"
            with patch.object(match, "generate_batch", side_effect=[[held(rows[0])], RuntimeError("offline")]):
                with self.assertRaisesRegex(RuntimeError, "offline"):
                    match.run(rows, output, "model-a", 1)
            previous = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual([item["targetCd"] for item in previous["matches"]], ["T1"])
            with patch.object(match, "generate_batch", return_value=[held(rows[1])]) as generate:
                match.run(rows, output, "model-a", 1)
                self.assertEqual(generate.call_args.args[0], [rows[1]])
            with self.assertRaisesRegex(ValueError, "another run"):
                match.run(rows, output, "model-b", 1)
            rows[1]["target"]["country"] = "다름"
            with self.assertRaisesRegex(ValueError, "another run"):
                match.run(rows, output, "model-a", 1)


if __name__ == "__main__":
    unittest.main()
