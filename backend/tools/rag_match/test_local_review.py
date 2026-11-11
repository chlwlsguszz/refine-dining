import unittest

from local_review import review


def food(code, site, time, state="생것", part="육"):
    return {"foodCd": code, "foodNm": f"대구_{part}_{state}_{site}_{time}",
            "srcCd": "2", "lv4Cd": "X", "lv6Cd": "X01",
            "lv7Nm": state, "lv7Cd": "01" if state == "생것" else "50",
            "basis": "100g", "country": "대한민국", "imported": "N",
            "region": "" if site == "대표" else site,
            "month": "" if time == "평균" else time[:-1].zfill(2)}


class LocalReviewTest(unittest.TestCase):
    def setUp(self):
        self.target = food("T", "대표", "평균", "구운것")
        self.mean = food("M", "여수", "평균")
        self.month = food("W", "대표", "5월")

    def result(self, *candidates):
        return review({"target": self.target, "candidates": list(candidates)})

    def test_priority_order_and_complete_direct_scope(self):
        local = food("L", "부산", "6월")
        same = food("D", "대표", "평균")
        for choices, expected, label in (
                ([self.mean, same], "D", "직접 비교"),
                ([self.month, self.mean], "M", "참고 비교"),
                ([local, self.month], "W", "참고 비교")):
            decision = self.result(*choices)
            self.assertEqual((decision["selectedCd"], decision["verdict"]), (expected, label))

    def test_tied_best_choices_held_in_either_order(self):
        other = food("A", "통영", "평균")
        for choices in ([self.mean, other], [other, self.mean]):
            self.assertIsNone(self.result(*choices)["selectedCd"])

    def test_part_and_country_checked_before_mean_preference(self):
        wrong_part = food("B", "여수", "평균", part="육(뱃살)")
        wrong_country = self.mean | {"country": "캐나다", "imported": "Y"}
        self.assertEqual(self.result(wrong_part, wrong_country, self.month)["selectedCd"], "W")
        self.assertEqual(self.result(wrong_part, wrong_country)["verdict"], "보류")

    def test_unknown_observation_or_country_leaves_selection_open(self):
        for unresolved in (self.mean | {"region": "다른지역"},
                           self.mean | {"country": "미상"},
                           self.month | {"month": "07"}):
            self.assertIsNone(self.result(unresolved, self.month)["selectedCd"])
        self.target["country"] = ""
        self.assertEqual(self.result(self.mean, self.month)["verdict"], "보류")


if __name__ == "__main__":
    unittest.main()
