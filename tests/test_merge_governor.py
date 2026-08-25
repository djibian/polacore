from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("merge_governor", ROOT / "scripts" / "merge_governor.py")
assert SPEC and SPEC.loader
governor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(governor)

BASE = "1" * 40
HEAD = "2" * 40
MERGE = "3" * 40


def fixture() -> tuple[dict, dict, dict]:
    policy = json.loads((ROOT / "config" / "merge_governor_policy_v1.json").read_text(encoding="utf-8"))
    task = {
        "source_issue": 51,
        "authorized_paths": ["scripts/example.py", "tests/test_example.py"],
        "acceptance_commands": [
            {"command": "python3 -m unittest -v tests/test_example.py", "check": "task-tests"}
        ],
    }
    checks = [
        {
            "name": "task-tests",
            "kind": "TEST",
            "workflow": "PolaCore Trusted Task Checks",
            "workflow_path": ".github/workflows/trusted-task-checks.yml",
            "workflow_sha": BASE,
            "run_id": 7001,
            "job_id": 8001,
            "head_sha": HEAD,
            "conclusion": "PASS",
        }
    ]
    verdicts = [
        {
            "role": "REVIEWER",
            "workflow": "PolaCore Task Reviewer",
            "workflow_path": ".github/workflows/task-reviewer.yml",
            "workflow_sha": BASE,
            "run_id": 7002,
            "job_id": 8002,
            "head_sha": HEAD,
            "verdict": "NON_BLOCKING",
            "independent": True,
        }
    ]
    certificate = {
        "schema": "polacore.merge-certificate/v1",
        "repository": "djibian/polacore",
        "pull_request": 52,
        "base_ref": "engineering",
        "base_sha": BASE,
        "head_repo": "djibian/polacore",
        "head_ref": "agent/task-51-example",
        "head_sha": HEAD,
        "assurance": "STANDARD",
        "task": task,
        "changes": [
            {
                "path": "scripts/example.py",
                "status": "MODIFIED",
                "old_mode": "100644",
                "new_mode": "100644",
            },
            {
                "path": "tests/test_example.py",
                "status": "MODIFIED",
                "old_mode": "100644",
                "new_mode": "100644",
            },
        ],
        "checks": checks,
        "verdicts": verdicts,
        "policy_version": policy["version"],
        "policy_sha256": governor.policy_digest(policy),
    }
    observation = {
        "schema": "polacore.merge-observation/v1",
        "repository": certificate["repository"],
        "pull_request": certificate["pull_request"],
        "base_ref": certificate["base_ref"],
        "base_sha": certificate["base_sha"],
        "current_engineering_sha": certificate["base_sha"],
        "head_repo": certificate["head_repo"],
        "head_ref": certificate["head_ref"],
        "head_sha": certificate["head_sha"],
        "head_sha_kind": "PULL_REQUEST_HEAD",
        "assurance": certificate["assurance"],
        "task": copy.deepcopy(task),
        "changes": copy.deepcopy(certificate["changes"]),
        "checks": copy.deepcopy(checks),
        "verdicts": copy.deepcopy(verdicts),
        "policy_version": certificate["policy_version"],
        "policy_sha256": certificate["policy_sha256"],
        "unresolved_review_threads": 0,
        "contradictory_evidence": [],
        "draft": False,
        "mergeable": True,
        "protection_bypass_requested": False,
        "merge": {"state": "OPEN"},
    }
    return policy, certificate, observation


class MergeGovernorContractTests(unittest.TestCase):
    @staticmethod
    def set_paths(certificate, observation, paths) -> None:
        changes = [
            {"path": path, "status": "MODIFIED", "old_mode": "100644", "new_mode": "100644"}
            for path in sorted(paths)
        ]
        certificate["changes"] = changes
        observation["changes"] = copy.deepcopy(changes)

    def assert_rejected(self, mutate) -> None:
        policy, certificate, observation = fixture()
        mutate(policy, certificate, observation)
        with self.assertRaises(governor.Rejected):
            governor.evaluate(policy, certificate, observation)

    def test_eligible_standard_pr_is_accepted(self) -> None:
        policy, certificate, observation = fixture()
        result = governor.evaluate(policy, certificate, observation)
        self.assertEqual(result["decision"], "ELIGIBLE")
        self.assertEqual(result["head_sha"], HEAD)

    def test_eligible_reinforced_pr_is_accepted(self) -> None:
        policy, certificate, observation = fixture()
        self.set_paths(certificate, observation, ["security/example.py"])
        certificate["task"]["authorized_paths"] = ["security/**"]
        observation["task"] = copy.deepcopy(certificate["task"])
        certificate["assurance"] = "REINFORCED"
        observation["assurance"] = "REINFORCED"
        security_check = {
            "name": "security-tests",
            "kind": "SECURITY",
            "workflow": "PolaCore Trusted Security Checks",
            "workflow_path": ".github/workflows/trusted-security-checks.yml",
            "workflow_sha": BASE,
            "run_id": 7003,
            "job_id": 8003,
            "head_sha": HEAD,
            "conclusion": "PASS",
        }
        certificate["checks"].append(security_check)
        observation["checks"] = copy.deepcopy(certificate["checks"])
        for role, run_id, job_id in (("LAB", 7004, 8004), ("ADVERSARY", 7005, 8005)):
            certificate["verdicts"].append(
                {
                    "role": role,
                    "workflow": f"PolaCore {role.title()}",
                    "workflow_path": f".github/workflows/{role.lower()}.yml",
                    "workflow_sha": BASE,
                    "run_id": run_id,
                    "job_id": job_id,
                    "head_sha": HEAD,
                    "verdict": "NON_BLOCKING",
                    "independent": True,
                }
            )
        observation["verdicts"] = copy.deepcopy(certificate["verdicts"])
        result = governor.evaluate(policy, certificate, observation)
        self.assertEqual(result["decision"], "ELIGIBLE")
        self.assertEqual(result["assurance"], "REINFORCED")

    def test_moved_head_sha_is_rejected(self) -> None:
        self.assert_rejected(lambda _p, _c, o: o.__setitem__("head_sha", "4" * 40))

    def test_stale_base_is_rejected(self) -> None:
        self.assert_rejected(lambda _p, _c, o: o.__setitem__("current_engineering_sha", "4" * 40))

    def test_stale_policy_version_is_rejected(self) -> None:
        def mutate(_policy, certificate, observation):
            certificate["policy_version"] = "old"
            observation["policy_version"] = "old"

        self.assert_rejected(mutate)

    def test_stale_policy_digest_is_rejected(self) -> None:
        def mutate(_policy, certificate, observation):
            certificate["policy_sha256"] = "sha256:" + "0" * 64
            observation["policy_sha256"] = certificate["policy_sha256"]

        self.assert_rejected(mutate)

    def test_policy_cannot_retarget_autonomy_to_main(self) -> None:
        def mutate(policy, certificate, observation):
            policy["integration_branch"] = "main"
            certificate["base_ref"] = "main"
            observation["base_ref"] = "main"
            certificate["policy_sha256"] = governor.policy_digest(policy)
            observation["policy_sha256"] = certificate["policy_sha256"]

        self.assert_rejected(mutate)

    def test_unauthorized_path_is_rejected(self) -> None:
        def mutate(_policy, certificate, observation):
            self.set_paths(certificate, observation, ["README.md"])

        self.assert_rejected(mutate)

    def test_candidate_modification_of_own_gate_is_rejected(self) -> None:
        def mutate(_policy, certificate, observation):
            paths = ["scripts/merge_governor.py"]
            self.set_paths(certificate, observation, paths)
            certificate["task"]["authorized_paths"] = paths
            observation["task"] = copy.deepcopy(certificate["task"])

        self.assert_rejected(mutate)

    def test_missing_check_is_rejected(self) -> None:
        def mutate(_policy, certificate, observation):
            certificate["checks"] = []
            observation["checks"] = []

        self.assert_rejected(mutate)

    def test_skipped_check_is_rejected(self) -> None:
        def mutate(_policy, certificate, observation):
            certificate["checks"][0]["conclusion"] = "SKIP"
            observation["checks"][0]["conclusion"] = "SKIP"

        self.assert_rejected(mutate)

    def test_candidate_controlled_check_workflow_is_rejected(self) -> None:
        def mutate(_policy, certificate, observation):
            certificate["checks"][0]["workflow_sha"] = HEAD
            observation["checks"][0]["workflow_sha"] = HEAD

        self.assert_rejected(mutate)

    def test_acceptance_command_without_named_check_is_rejected(self) -> None:
        def mutate(_policy, certificate, observation):
            certificate["task"]["acceptance_commands"][0]["check"] = "missing-check"
            observation["task"] = copy.deepcopy(certificate["task"])

        self.assert_rejected(mutate)

    def test_blocking_reviewer_is_rejected(self) -> None:
        def mutate(_policy, certificate, observation):
            certificate["verdicts"][0]["verdict"] = "BLOCKING"
            observation["verdicts"][0]["verdict"] = "BLOCKING"

        self.assert_rejected(mutate)

    def test_verdict_cannot_reuse_check_job(self) -> None:
        def mutate(_policy, certificate, observation):
            certificate["verdicts"][0]["job_id"] = certificate["checks"][0]["job_id"]
            observation["verdicts"] = copy.deepcopy(certificate["verdicts"])

        self.assert_rejected(mutate)

    def test_main_target_is_rejected(self) -> None:
        def mutate(_policy, certificate, observation):
            certificate["base_ref"] = "main"
            observation["base_ref"] = "main"

        self.assert_rejected(mutate)

    def test_fork_pr_is_rejected(self) -> None:
        def mutate(_policy, certificate, observation):
            certificate["head_repo"] = "attacker/polacore"
            observation["head_repo"] = "attacker/polacore"

        self.assert_rejected(mutate)

    def test_permission_workflow_change_is_rejected(self) -> None:
        def mutate(_policy, certificate, observation):
            paths = [".github/workflows/steal-token.yml"]
            self.set_paths(certificate, observation, paths)
            certificate["task"]["authorized_paths"] = [".github/workflows/**"]
            observation["task"] = copy.deepcopy(certificate["task"])

        self.assert_rejected(mutate)

    def test_security_constitution_change_is_rejected(self) -> None:
        def mutate(_policy, certificate, observation):
            paths = ["docs/security/INVARIANTS.md"]
            self.set_paths(certificate, observation, paths)
            certificate["task"]["authorized_paths"] = paths
            observation["task"] = copy.deepcopy(certificate["task"])

        self.assert_rejected(mutate)

    def test_synthetic_merge_sha_is_rejected(self) -> None:
        self.assert_rejected(lambda _p, _c, o: o.__setitem__("head_sha_kind", "SYNTHETIC_MERGE"))

    def test_symlink_change_is_rejected(self) -> None:
        def mutate(_policy, certificate, observation):
            certificate["changes"][0]["new_mode"] = "120000"
            observation["changes"][0]["new_mode"] = "120000"

        self.assert_rejected(mutate)

    def test_rename_status_is_rejected(self) -> None:
        def mutate(_policy, certificate, observation):
            certificate["changes"][0]["status"] = "RENAMED"
            observation["changes"][0]["status"] = "RENAMED"

        self.assert_rejected(mutate)

    def test_unresolved_review_thread_is_rejected(self) -> None:
        self.assert_rejected(lambda _p, _c, o: o.__setitem__("unresolved_review_threads", 1))

    def test_draft_is_rejected(self) -> None:
        self.assert_rejected(lambda _p, _c, o: o.__setitem__("draft", True))

    def test_non_mergeable_state_is_rejected(self) -> None:
        self.assert_rejected(lambda _p, _c, o: o.__setitem__("mergeable", False))

    def test_protection_bypass_is_rejected(self) -> None:
        self.assert_rejected(lambda _p, _c, o: o.__setitem__("protection_bypass_requested", True))

    def test_contradictory_evidence_is_rejected(self) -> None:
        self.assert_rejected(lambda _p, _c, o: o["contradictory_evidence"].append("stale reviewer"))

    def test_security_path_cannot_lower_assurance(self) -> None:
        def mutate(_policy, certificate, observation):
            paths = ["security/example.py"]
            self.set_paths(certificate, observation, paths)
            certificate["task"]["authorized_paths"] = ["security/**"]
            observation["task"] = copy.deepcopy(certificate["task"])

        self.assert_rejected(mutate)

    def test_objective_amendment_is_never_autonomous(self) -> None:
        def mutate(_policy, certificate, observation):
            certificate["assurance"] = "OBJECTIVE_AMENDMENT"
            observation["assurance"] = "OBJECTIVE_AMENDMENT"

        self.assert_rejected(mutate)

    def test_certificate_and_trusted_task_must_match(self) -> None:
        self.assert_rejected(lambda _p, _c, o: o["task"].__setitem__("source_issue", 999))

    def test_duplicate_merge_replay_is_idempotent(self) -> None:
        policy, certificate, observation = fixture()
        observation["current_engineering_sha"] = MERGE
        observation["merge"] = {
            "state": "MERGED",
            "head_sha": HEAD,
            "merge_sha": MERGE,
            "certificate_sha256": governor.digest(certificate),
        }
        result = governor.evaluate(policy, certificate, observation)
        self.assertEqual(result["decision"], "ALREADY_MERGED")
        self.assertEqual(result["merge_sha"], MERGE)

    def test_replay_with_different_certificate_is_rejected(self) -> None:
        policy, certificate, observation = fixture()
        observation["current_engineering_sha"] = MERGE
        observation["merge"] = {
            "state": "MERGED",
            "head_sha": HEAD,
            "merge_sha": MERGE,
            "certificate_sha256": "sha256:" + "0" * 64,
        }
        with self.assertRaises(governor.Rejected):
            governor.evaluate(policy, certificate, observation)


if __name__ == "__main__":
    unittest.main()
