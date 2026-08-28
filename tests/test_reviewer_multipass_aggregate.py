from __future__ import annotations

import copy
import unittest

from scripts import reviewer_multipass_aggregate as aggregate


def valid(
    pass_id: str,
    verdict: str = "READY_FOR_HUMAN",
    confidence: float = 0.90,
) -> dict:
    return {
        "schema": aggregate.PASS_SCHEMA,
        "case": "H1",
        "pass_id": pass_id,
        "status": "VALID",
        "decision": {
            "verdict": verdict,
            "confidence": confidence,
            "rationale": (
                f"{pass_id} reviewed the bounded candidate and found a concrete result."
            ),
        },
    }


def complete_set() -> list[dict]:
    return [valid(pass_id) for pass_id in aggregate.REQUIRED_PASSES]


class ReviewerMultipassAggregateTest(unittest.TestCase):
    def test_all_non_blocking_passes_are_complete(self) -> None:
        result = aggregate.aggregate(complete_set())
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["disposition"], "NON_BLOCKING")
        self.assertEqual(result["aggregate_verdict"], "READY_FOR_HUMAN")
        self.assertEqual(result["confidence_floor"], 0.90)
        self.assertEqual(result["blocking_passes"], [])
        self.assertEqual(result["failed_passes"], [])
        self.assertEqual(result["authority"], "INFERENCE_ONLY")

    def test_one_blocking_pass_cannot_be_outvoted(self) -> None:
        rows = complete_set()
        rows[1] = valid(rows[1]["pass_id"], "CHANGES_REQUIRED", 0.88)
        result = aggregate.aggregate(rows)
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["disposition"], "BLOCKING")
        self.assertEqual(result["aggregate_verdict"], "CHANGES_REQUIRED")
        self.assertEqual(
            result["blocking_passes"], ["implementation_consistency"]
        )

    def test_blocked_is_stronger_than_changes_required(self) -> None:
        rows = complete_set()
        rows[0] = valid(rows[0]["pass_id"], "CHANGES_REQUIRED", 0.80)
        rows[2] = valid(rows[2]["pass_id"], "BLOCKED", 0.70)
        result = aggregate.aggregate(rows)
        self.assertEqual(result["aggregate_verdict"], "BLOCKED")
        self.assertEqual(
            result["blocking_passes"],
            ["behavioral_semantics", "security_authority"],
        )

    def test_provider_failure_makes_aggregate_unproven(self) -> None:
        rows = complete_set()
        rows[2] = {
            "schema": aggregate.PASS_SCHEMA,
            "case": "H1",
            "pass_id": rows[2]["pass_id"],
            "status": "PROVIDER_FAILURE",
            "reason": "provider timeout",
        }
        result = aggregate.aggregate(rows)
        self.assertEqual(result["status"], "UNPROVEN")
        self.assertEqual(result["disposition"], "BLOCKING")
        self.assertEqual(result["aggregate_verdict"], "BLOCKED")
        self.assertEqual(result["failed_passes"], ["security_authority"])

    def test_invalid_output_makes_aggregate_unproven(self) -> None:
        rows = complete_set()
        rows[0] = {
            "schema": aggregate.PASS_SCHEMA,
            "case": "H1",
            "pass_id": rows[0]["pass_id"],
            "status": "MODEL_OUTPUT_INVALID",
            "reason": "validator rejected output",
        }
        result = aggregate.aggregate(rows)
        self.assertEqual(result["status"], "UNPROVEN")
        self.assertEqual(result["failed_passes"], ["behavioral_semantics"])

    def test_missing_pass_is_blocking_not_a_two_pass_majority(self) -> None:
        result = aggregate.aggregate(complete_set()[:2])
        self.assertEqual(result["status"], "UNPROVEN")
        self.assertEqual(result["disposition"], "BLOCKING")
        self.assertIn(
            "missing pass ids: security_authority",
            result["errors"],
        )

    def test_duplicate_pass_is_fail_closed(self) -> None:
        rows = complete_set()
        rows.append(copy.deepcopy(rows[0]))
        result = aggregate.aggregate(rows)
        self.assertEqual(result["status"], "UNPROVEN")
        self.assertIn(
            "duplicate pass ids: behavioral_semantics",
            result["errors"],
        )

    def test_case_mismatch_is_fail_closed(self) -> None:
        rows = complete_set()
        rows[2]["case"] = "H2"
        result = aggregate.aggregate(rows)
        self.assertEqual(result["status"], "UNPROVEN")
        self.assertIsNone(result["case"])
        self.assertIn(
            "pass records must bind to exactly one case",
            result["errors"],
        )

    def test_unexpected_pass_is_fail_closed(self) -> None:
        rows = complete_set()
        rows[2]["pass_id"] = "hidden_corpus_hint"
        result = aggregate.aggregate(rows)
        self.assertEqual(result["status"], "UNPROVEN")
        self.assertTrue(
            any("pass record id is unexpected" in item for item in result["errors"])
        )

    def test_low_confidence_nonblocking_record_is_rejected(self) -> None:
        rows = complete_set()
        rows[0] = valid(rows[0]["pass_id"], "READY_FOR_HUMAN", 0.59)
        result = aggregate.aggregate(rows)
        self.assertEqual(result["status"], "UNPROVEN")
        self.assertTrue(
            any("low-confidence" in item for item in result["errors"])
        )

    def test_input_order_does_not_change_aggregate_digest(self) -> None:
        rows = complete_set()
        first = aggregate.aggregate(rows)
        second = aggregate.aggregate(list(reversed(rows)))
        self.assertEqual(first["pass_digests"], second["pass_digests"])
        self.assertEqual(first["aggregate_digest"], second["aggregate_digest"])


if __name__ == "__main__":
    unittest.main()
