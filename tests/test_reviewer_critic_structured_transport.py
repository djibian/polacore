import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import reviewer_critic_structured_transport as mod


class ReviewerCriticStructuredTransportTest(unittest.TestCase):
    def _hypothesis(self):
        return {
            "severity": "BLOCKING",
            "location": "candidate.py: collect()",
            "claim": "A concrete control-flow path may contradict the stated success semantics.",
            "failure_mode": "A caller could receive a failure classification even when observation completed successfully.",
        }

    def test_request_is_qwen_strict_tool_free_schema(self):
        request = mod.build_request("bounded evidence", "system prompt")
        self.assertEqual(request["model"], "qwen3-coder-30b-A3b-instruct")
        self.assertEqual(request["tool_choice"], "none")
        self.assertEqual(request["response_format"]["type"], "json_schema")
        schema = request["response_format"]["json_schema"]
        self.assertTrue(schema["strict"])
        self.assertEqual(schema["schema"], mod.CRITIC_SCHEMA)
        self.assertFalse(schema["schema"]["additionalProperties"])

    def test_zero_hypotheses_is_valid(self):
        self.assertEqual(mod.validate_critic({"hypotheses": []}), {"hypotheses": []})

    def test_valid_hypothesis_is_preserved(self):
        item = self._hypothesis()
        result = mod.validate_critic({"hypotheses": [item]})
        self.assertEqual(result["hypotheses"], [item])

    def test_extra_keys_are_rejected(self):
        with self.assertRaises(ValueError):
            mod.validate_critic({"hypotheses": [], "verdict": "READY_FOR_HUMAN"})
        item = self._hypothesis(); item["extra"] = "no"
        with self.assertRaises(ValueError):
            mod.validate_critic({"hypotheses": [item]})

    def test_more_than_six_hypotheses_are_rejected(self):
        with self.assertRaises(ValueError):
            mod.validate_critic({"hypotheses": [self._hypothesis() for _ in range(7)]})

    def test_bad_severity_and_lengths_are_rejected(self):
        item = self._hypothesis(); item["severity"] = "READY_FOR_HUMAN"
        with self.assertRaises(ValueError):
            mod.validate_critic({"hypotheses": [item]})
        item = self._hypothesis(); item["claim"] = "too short"
        with self.assertRaises(ValueError):
            mod.validate_critic({"hypotheses": [item]})
        item = self._hypothesis(); item["location"] = "x" * 161
        with self.assertRaises(ValueError):
            mod.validate_critic({"hypotheses": [item]})

    def test_extract_requires_single_stop_choice(self):
        content = json.dumps({"hypotheses": [self._hypothesis()]})
        response = {"choices": [{"finish_reason": "stop", "message": {"content": content}}]}
        self.assertEqual(mod.extract_critic(response)["hypotheses"][0]["severity"], "BLOCKING")
        response["choices"][0]["finish_reason"] = "length"
        with self.assertRaises(ValueError):
            mod.extract_critic(response)

    def test_non_json_content_is_model_output_invalid(self):
        response = {"choices": [{"finish_reason": "stop", "message": {"content": "not json"}}]}
        with self.assertRaises(ValueError):
            mod.extract_critic(response)


if __name__ == "__main__":
    unittest.main()
