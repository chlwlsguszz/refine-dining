import tempfile
from pathlib import Path
import unittest

from grounded_rag import compare_records, explain_generation, retrieve_passages, validate_generation, validate_passages
from match import read_json
from run_local_rag import DATA, LocalLlama, generate_case


def food(code, name, group, state, basis="100g"):
    return {"foodCd": code, "foodNm": name, "lv4Cd": "G", "lv4Nm": "인삼", "lv5Cd": group,
            "lv5Nm": group, "lv6Cd": "00", "lv6Nm": "해당없음", "lv7Cd": "01" if state == "생것" else "99",
            "lv7Nm": state, "srcCd": "1", "srcNm": "식품성분표", "basis": basis, "imported": "N",
            "country": "해당없음", "region": "", "month": ""}


class GroundedRagTests(unittest.TestCase):
    def setUp(self):
        self.corpus = read_json(DATA / "evidence/passages.json")["passages"]
        self.target = food("T", "인삼_홍삼_말린것", "홍삼", "말린것")
        self.raw = food("R", "인삼_수삼_생것", "수삼", "생것")
        self.docs = retrieve_passages(self.target, self.corpus)
        _, self.allowed = compare_records(self.target, [self.raw], self.docs, 0)
        self.response = {"verdict": "참고 비교", "selectedCd": "R", "targetQuote": self.target["foodNm"],
                         "candidateQuote": self.raw["foodNm"], "citationId": self.docs[0]["id"],
                         "citationQuote": self.docs[0]["quote"], "differenceField": "foodNm"}

    def test_document_scope_is_required_before_relevance(self):
        validate_passages(self.corpus)
        self.assertEqual(["ginseng-red-art2-3"], [p["id"] for p in self.docs])
        extract = dict(self.target, lv7Nm="추출액")
        self.assertEqual([], retrieve_passages(extract, self.corpus))
        with self.assertRaises(ValueError):
            validate_passages([self.docs[0], self.docs[0]])

    def test_verified_selection_and_exact_citations(self):
        self.assertEqual("R", self.allowed["selectedCd"])
        diff = validate_generation(self.response, self.target, [self.raw], self.docs, self.allowed)
        self.assertEqual(self.raw["foodNm"], diff["candidate"])
        self.assertIn(self.docs[0]["quote"], explain_generation(self.response, self.target, [self.raw], self.docs, diff))

    def test_forged_citation_candidate_and_overstated_verdict_are_rejected(self):
        for changes in ({"citationId": "not-retrieved"}, {"citationQuote": "틀린 문장"},
                        {"candidateQuote": None}, {"selectedCd": "foreign"}, {"verdict": "직접 비교"},
                        {"citationQuote": None, "citationId": None}, {"differenceField": "basis"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_generation(dict(self.response, **changes), self.target, [self.raw], self.docs, self.allowed)

    def test_units_parts_tie_or_context_never_authorize_candidate(self):
        for raw, docs, boundary in ((dict(self.raw, basis="100mL"), self.docs, 0),
                                    (dict(self.raw, foodNm="인삼_수삼_잎_생것"), self.docs, 0),
                                    (self.raw, self.docs, 1),
                                    (self.raw, [dict(self.docs[0], use="process_context")], 0)):
            with self.subTest(raw=raw, boundary=boundary):
                _, allowed = compare_records(self.target, [raw], docs, boundary)
                self.assertIsNone(allowed["selectedCd"])
                with self.assertRaises(ValueError):
                    validate_generation(dict(self.response, candidateQuote=raw["foodNm"]), self.target, [raw],
                                        docs, allowed)

    def test_cache_is_input_versioned_and_model_failure_keeps_rules(self):
        calls = []
        reported = self.response

        class Stub:
            def generate(self, data, schema):
                calls.append(1)
                return {"response": reported, "usage": {"completion_tokens": 15}}

        with tempfile.TemporaryDirectory() as dir_name:
            def invoke(version, unavailable=None):
                return generate_case(Stub(), {"promptVersion": version}, {"target": self.target}, [self.raw],
                                     self.docs, self.allowed, Path(dir_name), unavailable)
            self.assertEqual("validated", invoke("1")["status"])
            self.assertTrue(invoke("1")["cacheHit"])
            self.assertFalse(invoke("2")["cacheHit"])
            self.assertEqual("unavailable", invoke("3", "disconnected")["status"])
            self.assertEqual(2, len(calls))
            self.assertEqual("R", self.allowed["selectedCd"])

    def test_non_local_and_redirect_targets_are_refused(self):
        for url in ("https://api.example.com", "http://127.0.0.1.example.org", "http://127.0.0.1@other.test",
                    "http://127.0.0.1:9999/other/path", "http://127.0.0.1:9999?x=1"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                LocalLlama(url)


if __name__ == "__main__":
    unittest.main()
