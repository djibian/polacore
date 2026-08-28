import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import reviewer_challenge_structured_transport as transport
from scripts import reviewer_executable_blind as blind
from scripts import reviewer_executable_historical as historical
from scripts import reviewer_executable_oracle as oracle


RATIONALE = "Check one concrete behavior using the exact same challenge on both revisions."


def challenge(code: str | None = None) -> dict[str, str]:
    return {
        "schema": historical.base.SCHEMA,
        "name": "challenge_live_contract",
        "rationale": RATIONALE,
        "code": code
        or """import candidate
import unittest

class CandidateTest(unittest.TestCase):
    def test_value(self):
        self.assertEqual(candidate.VALUE, 2)
""",
    }


def synthesis(status: str = "VALID") -> dict:
    cases = {}
    for token in sorted(oracle.CASES):
        if status == "VALID":
            cases[token] = {"status": "VALID", "challenge": challenge()}
        else:
            cases[token] = {"status": status, "reason": "bounded synthetic failure"}
    return {"schema": oracle.SYNTHESIS_SCHEMA, "model": oracle.MODEL, "cases": cases}


class BlindMaterializerTest(unittest.TestCase):
    def test_neutral_candidate_map_contains_no_h_labels(self):
        self.assertEqual(set(blind.CASES), {"alpha", "beta", "gamma", "delta"})
        self.assertTrue(all(len(sha) == 40 for sha in blind.CASES.values()))

    def test_blind_bundle_contains_candidate_evidence_but_no_hidden_oracle_metadata(self):
        fake_files = {
            "scripts/merge_provider_live_collect.py": b"VALUE = 1\n",
            "tests/test_merge_provider_live_collect.py": b"# tests\n",
            "docs/automation/MERGE_PROVIDER.md": b"provider contract\n",
        }
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "bundle.txt"
            with mock.patch.object(blind, "_git_show", side_effect=lambda sha, path: fake_files[path]):
                blind.build_bundle("alpha", out)
            text = out.read_text(encoding="utf-8")
        self.assertIn("Exact candidate SHA", text)
        self.assertIn("VALUE = 1", text)
        for spec in oracle.CASES.values():
            if spec.repair_sha is not None:
                self.assertNotIn(spec.repair_sha, text)
        self.assertNotIn("H1", text)
        self.assertNotIn("H2", text)
        self.assertNotIn("H3", text)
        self.assertNotIn("H4", text)


class ChallengeTransportTest(unittest.TestCase):
    def test_request_is_qwen_tool_free_strict_schema(self):
        request = transport.build_request("bounded evidence", "system")
        self.assertEqual(request["model"], "qwen3-coder-30b-A3b-instruct")
        self.assertEqual(request["tool_choice"], "none")
        self.assertTrue(request["response_format"]["json_schema"]["strict"])
        self.assertFalse(request["response_format"]["json_schema"]["schema"]["additionalProperties"])

    def test_extract_revalidates_historical_sandbox_contract(self):
        response = {
            "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(challenge())}}]
        }
        self.assertEqual(transport.extract_challenge(response)["name"], "challenge_live_contract")

        unsafe = challenge("""import candidate
import unittest

class CandidateTest(unittest.TestCase):
    def test_escape(self):
        self.assertIn("os", candidate.sys.modules)
""")
        response["choices"][0]["message"]["content"] = json.dumps(unsafe)
        with self.assertRaises(historical.HistoricalChallengeError):
            transport.extract_challenge(response)

    def test_non_stop_or_multiple_choices_fail_closed(self):
        for choices in (
            [],
            [{"finish_reason": "length", "message": {"content": "{}"}}],
            [
                {"finish_reason": "stop", "message": {"content": "{}"}},
                {"finish_reason": "stop", "message": {"content": "{}"}},
            ],
        ):
            with self.subTest(choices=choices):
                with self.assertRaises(ValueError):
                    transport.extract_challenge({"choices": choices})


class HiddenOracleTest(unittest.TestCase):
    def _fetcher(self, mismatch_support: bool = False):
        candidate_to_repair = {
            spec.candidate_sha: spec.repair_sha
            for spec in oracle.CASES.values()
            if spec.repair_sha is not None
        }
        repairs = {repair for repair in candidate_to_repair.values() if repair is not None}
        control_sha = oracle.CASES["delta"].candidate_sha

        def fetch(sha: str, path: str) -> bytes:
            if path == oracle.CANDIDATE_PATH:
                if sha in repairs or sha == control_sha:
                    return b"VALUE = 2\n"
                return b"VALUE = 1\n"
            if path.endswith("merge_governor.py"):
                if mismatch_support and sha == oracle.CASES["alpha"].repair_sha:
                    return b"VALUE = 99\n"
                return b"VALUE = 7\n"
            if path.endswith("merge_provider_capability.py"):
                return b"CAPABILITY = 'bounded'\n"
            raise AssertionError(path)

        return fetch

    def test_hidden_oracle_qualifies_synthetic_causal_corpus_only_for_repeat(self):
        result = oracle.evaluate(synthesis(), self._fetcher())
        self.assertEqual(result["historical_detected"], 3)
        self.assertEqual(result["negative_control"], "CLEAN_CONTROL")
        self.assertEqual(result["result"], "QUALIFIED_FOR_REPEAT")
        self.assertEqual(result["authority"], "EXECUTABLE_EVIDENCE_ONLY")

    def test_support_mismatch_is_unproven(self):
        result = oracle.evaluate(synthesis(), self._fetcher(mismatch_support=True))
        self.assertEqual(result["cases"]["alpha"]["outcome"], "UNPROVEN")
        self.assertEqual(result["result"], "NOT_QUALIFIED")

    def test_provider_or_invalid_output_never_becomes_execution_pass(self):
        for status in ("PROVIDER_FAILURE", "MODEL_OUTPUT_INVALID"):
            with self.subTest(status=status):
                result = oracle.evaluate(synthesis(status), self._fetcher())
                self.assertEqual(result["historical_detected"], 0)
                self.assertEqual(result["result"], "NOT_QUALIFIED")
                self.assertTrue(all(row["outcome"] == "UNPROVEN" for row in result["cases"].values()))

    def test_required_shas_bind_exact_hidden_pairs(self):
        shas = oracle.required_shas()
        self.assertEqual(len(shas), 7)
        self.assertEqual(len(set(shas)), 7)
        self.assertTrue(all(len(sha) == 40 for sha in shas))

    def test_synthesis_shape_is_exact(self):
        bad = synthesis()
        bad["cases"].pop("delta")
        with self.assertRaises(ValueError):
            oracle.evaluate(bad, self._fetcher())


if __name__ == "__main__":
    unittest.main()
