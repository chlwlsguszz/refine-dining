from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from release_evaluation import checked_freeze, freeze, reviewed_labels, score_rows


def example(target, selected, candidates):
    def food(code):
        return {"foodCd": code, "basis": "100g", "lv5Nm": "보리", "lv6Nm": "보리"}
    return {"targetCd": target, "target": food(target), "selectedCd": selected,
            "verdict": "참고 비교" if selected else "보류",
            "candidates": [{"record": food(code)} for code in candidates]}


def label(code, status, choices):
    return {"targetCd": code, "status": status, "selections": [{"foodCd": c, "verdict": "참고 비교"} for c in choices],
            "confirmed": True, "reviewer": "independent-test", "blinded": True, "independent": True,
            "reason": "original source", "evidence": ["source-test"], "exhaustive": True}


class EvaluationTests(unittest.TestCase):
    def test_repeated_freeze_cannot_replace_changed_recipe(self):
        with TemporaryDirectory() as directory:
            args = SimpleNamespace(output_dir=Path(directory))
            with patch("release_evaluation.release_recipe", return_value={"method": "dev-policy"}):
                fingerprint = freeze(args)
                self.assertEqual(freeze(args), fingerprint)
            with patch("release_evaluation.release_recipe", return_value={"method": "changed"}):
                with self.assertRaises(ValueError):
                    checked_freeze(args)
                with self.assertRaises(ValueError):
                    freeze(args)

    def test_undefined_metrics_when_no_independent_labels(self):
        metrics = score_rows([example("Q1", None, ["A"])], {})
        self.assertEqual(metrics["unjudged"], 1)
        self.assertEqual(metrics["verifiedNoMatch"], 0)
        self.assertIsNone(metrics["recallAt5"]["rate"])
        self.assertIsNone(metrics["mrrAt5"])
        self.assertIsNone(metrics["wrongSelectionRateAmongChecked"])

    def test_multigold_ranks_wrong_decision_and_denominators(self):
        cases = [example("Q1", "B", ["A", "B"]), example("Q2", "C", ["C"]),
                 example("Q3", None, ["C"]), example("Q4", "C", ["C"])]
        gold = {"Q1": label("Q1", "matched", ["B", "D"]), "Q2": label("Q2", "matched", ["A"]),
                "Q4": label("Q4", "no_match", [])}
        metrics = score_rows(cases, gold)
        self.assertEqual(metrics["recallAt5"], {"hits": 1, "eligible": 2, "rate": .5})
        self.assertEqual(metrics["mrrAt5"], .25)
        self.assertEqual(metrics["verifiedWrongSelections"], 2)
        self.assertEqual(metrics["checkedSelections"], 3)
        self.assertEqual(metrics["unjudged"], 1)
        self.assertEqual(metrics["verifiedNoMatch"], 1)

    def test_labels_require_source_review_and_exhaustiveness_for_catalog_no_match(self):
        record = label("Q", "no_match", [])
        doc = {"partition": "test", "snapshotId": "s", "reviews": [record]}
        self.assertEqual(reviewed_labels(doc, "s", {"Q"}, {"A"}), {"Q": record})
        for key in ("blinded", "independent", "exhaustive", "evidence", "reviewer"):
            changed = deepcopy(doc)
            changed["reviews"][0].pop(key)
            with self.assertRaises(ValueError):
                reviewed_labels(changed, "s", {"Q"}, {"A"})

    def test_partial_positive_does_not_establish_wrong_outside_choice(self):
        gold = label("Q", "matched", ["A"])
        gold["exhaustive"] = False
        metrics = score_rows([example("Q", "C", ["C"])], {"Q": gold})
        self.assertEqual(metrics["checkedSelections"], 0)


if __name__ == "__main__":
    unittest.main()
