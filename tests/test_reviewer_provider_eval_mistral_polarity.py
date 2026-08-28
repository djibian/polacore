from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import reviewer_provider_eval_mistral_polarity as mod  # noqa: E402


class MistralNegativeControlPolarityTest(unittest.TestCase):
    def _decision(self, verdict: str, rationale: str) -> pathlib.Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        path = pathlib.Path(td.name) / "decision.json"
        path.write_text(
            json.dumps(
                {"verdict": verdict, "confidence": 0.9, "rationale": rationale}
            ),
            encoding="utf-8",
        )
        return path

    def test_historical_h3_detection_is_unchanged(self) -> None:
        path = self._decision(
            "CHANGES_REQUIRED",
            "The default urllib redirect behavior can replay the Authorization bearer token to a redirect target.",
        )
        result = mod.score("H3", path)
        self.assertEqual(result["status"], "DETECTED")
        self.assertTrue(result["known_signature_matches"]["H3"])

    def test_h4_repaired_redirect_statement_is_clean(self) -> None:
        path = self._decision(
            "READY_FOR_HUMAN",
            "The client uses a fixed endpoint allowlist, requires a non-empty token, and rejects redirects before authentication can leave the trusted destination.",
        )
        result = mod.score("H4", path)
        self.assertTrue(result["known_signature_matches"]["H3"])
        self.assertFalse(result["known_defect_claims"]["H3"])
        self.assertEqual(result["status"], "CLEAN_CONTROL")

    def test_h4_actual_redirect_leak_claim_remains_false_positive(self) -> None:
        path = self._decision(
            "READY_FOR_HUMAN",
            "Authorization token is still replayed across redirects to another target.",
        )
        result = mod.score("H4", path)
        self.assertTrue(result["known_defect_claims"]["H3"])
        self.assertEqual(result["status"], "FALSE_POSITIVE")

    def test_h4_blocking_redirect_leak_claim_remains_false_positive(self) -> None:
        path = self._decision(
            "CHANGES_REQUIRED",
            "Default redirect handling can forward the bearer credential to a redirect target.",
        )
        result = mod.score("H4", path)
        self.assertTrue(result["known_defect_claims"]["H3"])
        self.assertEqual(result["status"], "FALSE_POSITIVE")

    def test_protection_clause_does_not_mask_later_leak_claim(self) -> None:
        path = self._decision(
            "READY_FOR_HUMAN",
            "The primary client rejects redirects. However, a fallback can replay the Authorization token across redirects.",
        )
        result = mod.score("H4", path)
        self.assertTrue(result["known_defect_claims"]["H3"])
        self.assertEqual(result["status"], "FALSE_POSITIVE")

    def test_other_known_defect_signatures_are_not_suppressed(self) -> None:
        path = self._decision(
            "READY_FOR_HUMAN",
            "Collection success is incorrectly tied to merge eligibility, so a valid observation can be treated as failure.",
        )
        result = mod.score("H4", path)
        self.assertTrue(result["known_defect_claims"]["H1"])
        self.assertEqual(result["status"], "FALSE_POSITIVE")


if __name__ == "__main__":
    unittest.main()
