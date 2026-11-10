import unittest

from dev_match_policy import decide


def observation(code, name, *, state_code, state_name, **fields):
    record = dict(foodCd=code, foodNm=name, srcCd="1", srcNm="출처",
                  lv4Cd="W", lv4Nm="밀", lv5Cd="W0", lv5Nm="해당없음",
                  lv6Cd="W00", lv6Nm="해당없음", lv7Cd=state_code, lv7Nm=state_name,
                  basis="100g", country="해당없음", region="", month="", imported="N")
    return {**record, **fields}


def flour():
    return observation("T", "밀_통밀가루_분말화한것", state_code="06", state_name="분말화한것",
                       lv5Nm="통밀가루", lv6Cd="W10")


def raw(code="A", name="밀_통밀_생것", **fields):
    return observation(code, name, state_code="01", state_name="생것", **fields)


class DevelopmentPolicyTests(unittest.TestCase):
    def test_whole_grain_flour_preserves_specific_ingredient_but_origin_remains_unverified(self):
        wrong = raw("B", "밀_금강밀_도정_생것")
        choice = decide(flour(), [wrong, raw(lv6Nm="통밀")])
        self.assertEqual((choice["verdict"], choice["selectedCd"]), ("참고 비교", "A"))
        self.assertEqual(choice["targetQuote"], flour()["foodNm"])
        self.assertEqual(choice["candidateQuote"], "밀_통밀_생것")
        self.assertIn("원산지명이 미기재", choice["reason"])
        self.assertEqual([row["flag"] for row in choice["assessments"]], ["insufficient", "reference"])

    def test_order_and_unexamined_ties_do_not_create_a_winner(self):
        for candidates in ([raw(), raw("B")], [raw("B"), raw()]):
            self.assertIsNone(decide(flour(), candidates)["selectedCd"])
        self.assertIsNone(decide(flour(), [raw()], boundary_ties=1)["selectedCd"])

    def test_evidence_conflicts_and_contested_context(self):
        self.assertEqual(decide(flour(), [raw(basis="100mL")])["assessments"][0]["flag"], "conflict")
        self.assertEqual(decide(dict(flour(), imported="Y", country="미국"),
                                [raw(imported="Y", country="캐나다")])["assessments"][0]["flag"], "conflict")
        self.assertEqual(decide(flour(), [raw(country="미국")])["verdict"], "보류")
        target = observation("T", "대구류_대구_간_조린것_수입_평균", state_code="60", state_name="조린것")
        self.assertEqual(decide(target, [raw(name="대구류_대구_적색육_생것_수입_평균")])
                         ["assessments"][0]["flag"], "conflict")

    def test_generic_grape_and_product_without_source_mapping_abstain(self):
        grapes = observation("T", "포도_말린것", state_code="02", state_name="말린것")
        self.assertIsNone(decide(grapes, [raw(name="포도_거봉_생것"), raw("B", "포도_생것")])["selectedCd"])
        seafood = observation("T", "새우류_젓새우_전체_젓갈_대표_평균", state_code="71", state_name="젓갈")
        self.assertEqual(decide(seafood, [raw(name="새우류_젓새우_전체_생것_대표_평균")])["verdict"], "보류")
        imported = observation("T", "포도_수입산_말린것", state_code="02", state_name="말린것",
                               imported="Y", country="미국")
        self.assertEqual(decide(imported, [raw(name="포도_수입산_생것", imported="Y", country="미국")])["verdict"], "보류")

    def test_explicit_identity_and_equal_observation_are_required_for_direct(self):
        identity = dict(lv4Cd="fish", lv5Nm="참돔", lv6Cd="fish-meat", country="대한민국")
        target = observation("T", "돔류_참돔_육_찐것_대표_평균", state_code="49", state_name="찐것", **identity)
        fish = raw(name="돔류_참돔_육_생것_대표_평균", **identity)
        self.assertEqual(decide(target, [fish])["verdict"], "직접 비교")
        self.assertEqual(decide(target, [dict(fish, foodNm="돔류_참돔_육_생것_포항_평균", region="포항")])
                         ["verdict"], "참고 비교")


if __name__ == "__main__":
    unittest.main()
