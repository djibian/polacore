from __future__ import annotations

import ast
import copy
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import merge_certificate_build as builder  # noqa: E402
import merge_governor as governor  # noqa: E402
import merge_observation_collect as collector  # noqa: E402
from tests.test_merge_observation_collect import fixture as observation_fixture  # noqa: E402


CLAIM_FIELDS = {
    "repository",
    "pull_request",
    "base_ref",
    "base_sha",
    "head_repo",
    "head_ref",
    "head_sha",
    "changes",
    "checks",
    "verdicts",
}


def fixture() -> tuple[dict, dict, dict, dict]:
    policy, manifest, snapshot = observation_fixture()
    observation = collector.collect(policy, manifest, snapshot)
    claims = {key: copy.deepcopy(observation[key]) for key in CLAIM_FIELDS}
    claims["schema"] = builder.CLAIMS_SCHEMA
    return policy, manifest, claims, observation


class MergeCertificateBuildTests(unittest.TestCase):
    def assert_rejected(self, mutate) -> None:
        policy, manifest, claims, _observation = fixture()
        mutate(policy, manifest, claims)
        with self.assertRaises(governor.Rejected):
            builder.build_certificate(policy, manifest, claims)

    def test_certificate_and_independent_observation_reach_governor(self) -> None:
        policy, manifest, claims, observation = fixture()
        certificate = builder.build_certificate(policy, manifest, claims)
        result = governor.evaluate(policy, certificate, observation)
        self.assertEqual(result["decision"], "ELIGIBLE")
        self.assertEqual(certificate["task"]["source_issue"], manifest["source_issue"])
        self.assertEqual(certificate["policy_sha256"], governor.policy_digest(policy))

    def test_claims_cannot_supply_task_assurance_or_policy_authority(self) -> None:
        for field in ("task", "assurance", "policy_version", "policy_sha256"):
            with self.subTest(field=field):
                self.assert_rejected(lambda _p, _m, c, field=field: c.__setitem__(field, "attacker"))

    def test_pull_request_must_match_trusted_manifest(self) -> None:
        self.assert_rejected(lambda _p, _m, c: c.__setitem__("pull_request", 53))

    def test_repository_and_base_are_fixed_by_policy(self) -> None:
        self.assert_rejected(lambda _p, _m, c: c.__setitem__("repository", "attacker/polacore"))
        self.assert_rejected(lambda _p, _m, c: c.__setitem__("base_ref", "main"))

    def test_head_must_be_in_repository_agent_branch(self) -> None:
        self.assert_rejected(lambda _p, _m, c: c.__setitem__("head_repo", "attacker/polacore"))
        self.assert_rejected(lambda _p, _m, c: c.__setitem__("head_ref", "feature/untrusted"))

    def test_base_and_head_must_differ(self) -> None:
        self.assert_rejected(lambda _p, _m, c: c.__setitem__("head_sha", c["base_sha"]))

    def test_check_set_must_exactly_match_manifest(self) -> None:
        self.assert_rejected(lambda _p, _m, c: c.__setitem__("checks", []))

        def add_extra(_policy, _manifest, claims):
            extra = copy.deepcopy(claims["checks"][0])
            extra["name"] = "candidate-extra"
            extra["job_id"] += 100
            claims["checks"].append(extra)

        self.assert_rejected(add_extra)

    def test_check_identity_is_bound_to_manifest(self) -> None:
        for field, value in (
            ("kind", "SECURITY"),
            ("workflow", "Candidate Workflow"),
            ("workflow_path", ".github/workflows/candidate.yml"),
        ):
            with self.subTest(field=field):
                self.assert_rejected(
                    lambda _p, _m, c, field=field, value=value: c["checks"][0].__setitem__(field, value)
                )

    def test_check_must_be_bound_to_exact_base_and_head(self) -> None:
        self.assert_rejected(
            lambda _p, _m, c: c["checks"][0].__setitem__("workflow_sha", "9" * 40)
        )
        self.assert_rejected(lambda _p, _m, c: c["checks"][0].__setitem__("head_sha", "9" * 40))

    def test_verdict_set_and_identity_are_bound_to_manifest(self) -> None:
        self.assert_rejected(lambda _p, _m, c: c.__setitem__("verdicts", []))
        self.assert_rejected(
            lambda _p, _m, c: c["verdicts"][0].__setitem__("workflow_path", ".github/workflows/fake.yml")
        )

    def test_check_and_verdict_may_not_reuse_job(self) -> None:
        self.assert_rejected(
            lambda _p, _m, c: c["verdicts"][0].__setitem__("job_id", c["checks"][0]["job_id"])
        )

    def test_claimed_change_must_remain_inside_task_authority(self) -> None:
        self.assert_rejected(
            lambda _p, _m, c: c.__setitem__(
                "changes",
                [{"path": "src/other.py", "status": "ADDED", "old_mode": None, "new_mode": "100644"}],
            )
        )

    def test_forbidden_authority_path_is_rejected_even_if_manifest_lists_it(self) -> None:
        def mutate(_policy, manifest, claims):
            path = ".github/workflows/pwn.yml"
            manifest["authorized_paths"] = [path]
            claims["changes"] = [{"path": path, "status": "ADDED", "old_mode": None, "new_mode": "100644"}]

        self.assert_rejected(mutate)

    def test_path_floor_cannot_be_lowered_by_manifest(self) -> None:
        def mutate(_policy, manifest, claims):
            manifest["authorized_paths"] = ["security/example.py"]
            claims["changes"] = [
                {"path": "security/example.py", "status": "ADDED", "old_mode": None, "new_mode": "100644"}
            ]

        self.assert_rejected(mutate)

    def test_objective_amendment_cannot_be_certified(self) -> None:
        self.assert_rejected(lambda _p, m, _c: m.__setitem__("assurance", "OBJECTIVE_AMENDMENT"))

    def test_non_regular_git_mode_is_rejected(self) -> None:
        self.assert_rejected(lambda _p, _m, c: c["changes"][0].__setitem__("new_mode", "120000"))

    def test_workflow_path_is_part_of_the_certificate(self) -> None:
        policy, manifest, claims, _observation = fixture()
        certificate = builder.build_certificate(policy, manifest, claims)
        self.assertEqual(
            certificate["checks"][0]["workflow_path"],
            manifest["checks"][0]["workflow_path"],
        )
        self.assertEqual(
            certificate["verdicts"][0]["workflow_path"],
            manifest["verdicts"][0]["workflow_path"],
        )

    def test_trusted_contract_has_no_network_or_process_import(self) -> None:
        forbidden = {
            "aiohttp",
            "boto3",
            "ctypes",
            "ftplib",
            "http",
            "importlib",
            "os",
            "paramiko",
            "requests",
            "socket",
            "subprocess",
            "urllib",
        }
        for relative in (
            "scripts/merge_governor.py",
            "scripts/merge_observation_collect.py",
            "scripts/merge_certificate_build.py",
            "scripts/merge_decision_bundle.py",
            "scripts/merge_controller_protocol.py",
            "scripts/merge_provider_capability.py",
        ):
            with self.subTest(path=relative):
                tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
                imported: set[str] = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        imported.update(alias.name.split(".")[0] for alias in node.names)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imported.add(node.module.split(".")[0])
                self.assertFalse(imported & forbidden, f"forbidden authority import in {relative}")


if __name__ == "__main__":
    unittest.main()
