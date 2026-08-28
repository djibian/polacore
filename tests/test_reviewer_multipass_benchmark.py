from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import reviewer_multipass_aggregate as multipass
from scripts import reviewer_multipass_benchmark as benchmark


def decision(verdict: str = "READY_FOR_HUMAN", confidence: float = 0.90) -> dict:
    return {
        "verdict": verdict,
        "confidence": confidence,
        "rationale": "This independent pass found a concrete bounded review result in the supplied candidate.",
    }


class ReviewerMultipassBenchmarkTest(unittest.TestCase):
    def test_valid_record_preserves_validated_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "decision.json"
            path.write_text(json.dumps(decision("CHANGES_REQUIRED", 0.88)), encoding="utf-8")
            row = benchmark.valid_record("H1", "behavioral_semantics", path)
        self.assertEqual(row["status"], "VALID")
        self.assertEqual(row["decision"]["verdict"], "CHANGES_REQUIRED")
        self.assertEqual(row["decision"]["confidence"], 0.88)

    def test_failure_record_is_fail_closed_input(self) -> None:
        row = benchmark.failure_record(
            "H2", "implementation_consistency", "PROVIDER_FAILURE", "timeout"
        )
        result = multipass.aggregate(
            [
                row,
                benchmark.failure_record(
                    "H2", "behavioral_semantics", "MODEL_OUTPUT_INVALID", "bad json"
                ),
                benchmark.failure_record(
                    "H2", "security_authority", "PROVIDER_FAILURE", "network"
                ),
            ]
        )
        self.assertEqual(result["status"], "UNPROVEN")
        self.assertEqual(result["disposition"], "BLOCKING")

    def _write_case(
        self,
        root: Path,
        case: str,
        detected_passes: set[str],
        aggregate_disposition: str = "BLOCKING",
        clean_control: bool = False,
    ) -> None:
        case_dir = root / case
        case_dir.mkdir(parents=True)
        records = []
        for pass_id in multipass.REQUIRED_PASSES:
            verdict = "READY_FOR_HUMAN"
            if case != "H4" and pass_id in detected_passes:
                verdict = "CHANGES_REQUIRED"
            record = {
                "schema": multipass.PASS_SCHEMA,
                "case": case,
                "pass_id": pass_id,
                "status": "VALID",
                "decision": decision(verdict),
            }
            records.append(record)
            if case == "H4":
                score_status = "CLEAN_CONTROL" if clean_control else "FALSE_POSITIVE"
            else:
                score_status = "DETECTED" if pass_id in detected_passes else "MISSED"
            score = {
                "case": case,
                "model": benchmark.MODEL,
                "status": score_status,
            }
            (case_dir / f"{pass_id}.score.json").write_text(
                json.dumps(score), encoding="utf-8"
            )
        aggregate = multipass.aggregate(records)
        if case == "H4" and aggregate_disposition == "NON_BLOCKING":
            self.assertEqual(aggregate["disposition"], "NON_BLOCKING")
        (case_dir / "aggregate.json").write_text(
            json.dumps(aggregate), encoding="utf-8"
        )

    def test_qualification_requires_each_historical_case_and_clean_nonblocking_h4(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_case(root, "H1", {"behavioral_semantics"})
            self._write_case(root, "H2", {"implementation_consistency"})
            self._write_case(root, "H3", {"security_authority"})
            self._write_case(
                root,
                "H4",
                set(),
                aggregate_disposition="NON_BLOCKING",
                clean_control=True,
            )
            result = benchmark.summarize(root)
        self.assertEqual(result["historical_detected"], 3)
        self.assertEqual(result["negative_control"], "CLEAN_NON_BLOCKING")
        self.assertEqual(result["result"], "QUALIFIED_FOR_REPEAT")
        self.assertEqual(result["authority"], "INFERENCE_ONLY")

    def test_h4_blocking_verdict_prevents_qualification_even_if_signatures_are_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_case(root, "H1", {"behavioral_semantics"})
            self._write_case(root, "H2", {"implementation_consistency"})
            self._write_case(root, "H3", {"security_authority"})
            self._write_case(root, "H4", set(), clean_control=True)
            h4_dir = root / "H4"
            records = []
            for pass_id in multipass.REQUIRED_PASSES:
                verdict = "CHANGES_REQUIRED" if pass_id == "security_authority" else "READY_FOR_HUMAN"
                records.append(
                    {
                        "schema": multipass.PASS_SCHEMA,
                        "case": "H4",
                        "pass_id": pass_id,
                        "status": "VALID",
                        "decision": decision(verdict),
                    }
                )
            (h4_dir / "aggregate.json").write_text(
                json.dumps(multipass.aggregate(records)), encoding="utf-8"
            )
            result = benchmark.summarize(root)
        self.assertEqual(result["negative_control"], "FAILED")
        self.assertEqual(result["result"], "NOT_QUALIFIED")

    def test_missing_pass_score_prevents_qualification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_case(root, "H1", {"behavioral_semantics"})
            self._write_case(root, "H2", {"implementation_consistency"})
            self._write_case(root, "H3", {"security_authority"})
            self._write_case(
                root,
                "H4",
                set(),
                aggregate_disposition="NON_BLOCKING",
                clean_control=True,
            )
            (root / "H2" / "implementation_consistency.score.json").unlink()
            result = benchmark.summarize(root)
        self.assertFalse(result["historical_cases"]["H2"])
        self.assertEqual(result["result"], "NOT_QUALIFIED")


if __name__ == "__main__":
    unittest.main()
