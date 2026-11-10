import unittest

from audit_evidence import DEFAULT_DATASET, build, clear_exclusion, in_scope


class EvidenceAuditTest(unittest.TestCase):
    def test_development_only_and_source_boundaries(self):
        report = build(DEFAULT_DATASET)
        rows = report["rows"]
        self.assertEqual(len({row["target"]["foodCd"] for row in rows}), 74)
        self.assertEqual(sum(report["summary"]["primaryCounts"].values()), 74)
        checks = report["sourceOnlyChecks"]["rows"]
        self.assertEqual(len(checks), 77)
        supported = {row["targetQuote"]: row["referenceCandidates"] for row in checks if row["referenceCandidates"]}
        self.assertEqual(set(supported), {"인삼_백삼_말린것", "인삼_홍삼_말린것"})
        for candidates in supported.values():
            self.assertEqual([c["foodNm"] for c in candidates], ["인삼_수삼_생것"])
            self.assertTrue(candidates[0]["passageIds"])
        extract = next(r for r in rows if r["target"]["foodNm"] == "인삼_홍삼_추출")
        self.assertEqual(extract["primary"], "basis")
        self.assertEqual(extract["applicablePassageIds"], [])

    def test_missing_basis_and_part_overlap_remain_unjudged(self):
        a = {"basis": None, "lv5Nm": "대구", "lv6Nm": "전체"}
        b = {"basis": "100g", "lv5Nm": "대구", "lv6Nm": "육"}
        self.assertIsNone(clear_exclusion(a, b))

    def test_broad_process_definition_does_not_apply_to_unrelated_state(self):
        document = {"scope": {"families": [], "processed": [], "states": ["젓갈"]}}
        food = {"lv4Nm": "새우류", "lv5Nm": "젓새우", "lv7Nm": "말린것"}
        self.assertFalse(in_scope(food, document))


if __name__ == "__main__":
    unittest.main()
