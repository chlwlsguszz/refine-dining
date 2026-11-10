import unittest

from week1_cohort import build_packet, discover


def item(code, family, middle, sub, state, *, source="1", name=None, basis="100g", family_name=None):
    return {"food_cd": code, "food_nm": name or code, "src_cd": source,
            "food_lv4cd": family, "food_lv4nm": family_name or family,
            "food_lv5cd": middle, "food_lv6cd": sub, "food_lv7cd": state,
            "nut_con_srtr_qua": basis}


class DiscoveryTests(unittest.TestCase):
    def test_cross_source_parent_and_exact_preceding_state_are_not_missing_parents(self):
        rows = [
            item("raw", "grain", "wheat", "seed", "01"),
            item("milled", "grain", "wheat", "flour", "06"),
            item("cooked-sea", "grain", "wheat", "sea", "46"),
            item("prefiltered-sea", "unrelated", "different", "sea", "01", source="2"),
            item("dried", "grain", "noodle", "pasta", "02"),
            item("boiled-after-drying", "grain", "noodle", "pasta", "83"),
            item("different-basis", "grain", "noodle", "pasta", "83", basis="100mL"),
            item("no-shared-source", "grain", "wheat", "other", "46", source="3"),
        ]
        raw_foods, targets = discover(rows)
        indexed = {row["food_cd"]: (stratum, n) for row, _, stratum, n in targets}
        self.assertEqual(indexed, {"milled": ("same_lv5", 1), "dried": ("lv4_only", 0),
                                   "different-basis": ("lv4_only", 0)})
        self.assertEqual({r["food_cd"] for r in raw_foods}, {"raw", "prefiltered-sea"})

    def test_families_stay_together_order_is_reproducible_and_packet_is_unlabeled(self):
        rows = []
        for i in range(12):
            family = f"F{i:02d}"
            # Distinct codes carrying the same official name must remain on the same side.
            name = "메밀 국수" if i == 1 else ("메밀국수" if i == 2 else family)
            rows.extend([
                item(f"R{i}", family, "A", "R" + family, "01", family_name=name),
                item(f"C{i}a", family, "A", "C" + family, "46", family_name=name),
                item(f"C{i}b", family, "B", "C" + family, "58", family_name=name),
            ])
        manifest, packet = build_packet(rows, "snapshot", review_size=8)
        again = build_packet(list(reversed(rows)), "snapshot", review_size=8)
        self.assertEqual((manifest, packet), again)
        entries = manifest["rows"]
        self.assertEqual(len(entries), 24)
        test = {e["familyCode"] for e in entries if e["split"] == "test"}
        development = {e["familyCode"] for e in entries if e["split"].startswith("dev_")}
        self.assertTrue(test)
        self.assertFalse(test & development)
        self.assertEqual({e["familyCode"] for e in entries if e["lv4Cd"] in {"F01", "F02"}}, {"F01"})
        review = {e["targetCd"] for e in entries if e["split"] == "dev_review"}
        self.assertEqual(len(review), 8)
        self.assertEqual({c["target"]["foodCd"] for c in packet["cases"]}, review)
        self.assertEqual({e["stratumId"] for e in entries if e["targetCd"] in review}, {"same_lv5", "lv4_only"})
        catalog = {record["foodCd"]: record for record in packet["catalog"]}
        for case in packet["cases"]:
            self.assertTrue(case["candidateCds"])
            self.assertTrue(all(c in catalog for c in case["candidateCds"]))
            self.assertFalse({"selectedCd", "verdict", "acceptable"} & case.keys())
            self.assertIn("rawFields", case["target"])
        rows[0]["trace_field"] = "updated"
        _, changed_packet = build_packet(rows, "snapshot", review_size=8)
        self.assertNotEqual(packet["packetId"], changed_packet["packetId"])


if __name__ == "__main__":
    unittest.main()
