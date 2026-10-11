import json
import unittest
from evaluator import check_answer, evaluate

CASE = {"id": "a", "answerable": True, "allowed_citations": ["doc#1"],
        "required_citations": ["doc#1"], "required_terms": ["retry"], "forbidden_terms": ["canary"]}
ANSWER = {"answer": "Retry safely.", "citations": ["doc#1"], "abstained": False}


def run(**updates):
    return dict(variant="v1", case_id="a", output=json.dumps(ANSWER),
                input_tokens=100, output_tokens=50, latency_ms=12) | updates


class EvalTests(unittest.TestCase):
    def test_valid_answer_and_cost(self):
        result = evaluate([CASE], [run()], "1", "2")["v1"]
        self.assertEqual(result["pass_rate"], 1)
        self.assertEqual(result["estimated_cost_usd"], "0.0002")

    def test_bad_json_and_schema(self):
        self.assertEqual(check_answer("not json", CASE), ["invalid_json"])
        self.assertEqual(check_answer('{"answer": 2}', CASE), ["schema"])

    def test_unknown_and_missing_citation(self):
        errors = check_answer(json.dumps(ANSWER | {"citations": ["other"]}), CASE)
        self.assertEqual(set(errors), {"unknown_citation", "missing_citation"})

    def test_missing_case_reduces_score(self):
        result = evaluate([CASE, CASE | {"id": "b"}], [run()])["v1"]
        self.assertEqual(result["pass_rate"], 0.5)
        self.assertEqual(result["missing_cases"], ["b"])

    def test_canary_and_abstention(self):
        self.assertIn("forbidden_content", check_answer(json.dumps(ANSWER | {"answer": "retry canary"}), CASE))
        unknown = CASE | {"answerable": False}
        self.assertIn("failed_to_abstain", check_answer(json.dumps(ANSWER), unknown))
        abstained = json.dumps({"answer": "", "citations": [], "abstained": True})
        self.assertEqual(check_answer(abstained, unknown), [])

    def test_duplicate_and_unknown_cases_fail(self):
        for rows in ([run(), run()], [run(case_id="missing")]):
            with self.assertRaises(ValueError):
                evaluate([CASE], rows)

    def test_invalid_telemetry(self):
        for changes in ({"input_tokens": True}, {"latency_ms": float("nan")}, {"output_tokens": -1}):
            with self.assertRaises(ValueError):
                evaluate([CASE], [run(**changes)])

    def test_latency_uses_nearest_rank(self):
        cases = [CASE | {"id": str(i)} for i in range(20)]
        rows = [run(case_id=str(i), latency_ms=i+1) for i in range(20)]
        self.assertEqual(evaluate(cases, rows)["v1"]["p95_latency_ms"], 19)


if __name__ == "__main__":
    unittest.main()
