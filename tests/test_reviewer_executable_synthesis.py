import unittest

from scripts import reviewer_executable_synthesis as synthesis


CHALLENGE = {
    "schema": "polacore.reviewer-executable-challenge/v1",
    "name": "challenge_synthesis_contract",
    "rationale": "Exercise one bounded candidate behavior for deterministic causal verification.",
    "code": """import candidate
import unittest

class CandidateTest(unittest.TestCase):
    def test_value(self):
        self.assertTrue(candidate.VALUE)
""",
}


class SynthesisAssemblyTest(unittest.TestCase):
    def test_valid_and_failure_records_preserve_status(self):
        valid = synthesis.record("alpha", "VALID", challenge=CHALLENGE)
        failed = synthesis.record("beta", "PROVIDER_FAILURE", reason="bounded provider failure")
        self.assertEqual(valid["status"], "VALID")
        self.assertEqual(failed["status"], "PROVIDER_FAILURE")
        self.assertNotIn("challenge", failed)

    def test_summary_requires_exact_neutral_case_set(self):
        rows = [
            synthesis.record("alpha", "VALID", challenge=CHALLENGE),
            synthesis.record("beta", "MODEL_OUTPUT_INVALID", reason="invalid model output"),
            synthesis.record("gamma", "PROVIDER_FAILURE", reason="provider failed"),
            synthesis.record("delta", "VALID", challenge=CHALLENGE),
        ]
        result = synthesis.summarize(rows)
        self.assertEqual(set(result["cases"]), synthesis.CASES)
        self.assertEqual(result["cases"]["beta"]["status"], "MODEL_OUTPUT_INVALID")
        self.assertEqual(result["cases"]["gamma"]["status"], "PROVIDER_FAILURE")

    def test_missing_duplicate_or_empty_failure_reason_fails_closed(self):
        with self.assertRaises(ValueError):
            synthesis.summarize([
                synthesis.record("alpha", "VALID", challenge=CHALLENGE),
            ])
        row = synthesis.record("alpha", "VALID", challenge=CHALLENGE)
        with self.assertRaises(ValueError):
            synthesis.summarize([row, row])
        with self.assertRaises(ValueError):
            synthesis.record("beta", "PROVIDER_FAILURE", reason="   ")


if __name__ == "__main__":
    unittest.main()
