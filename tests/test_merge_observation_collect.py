from __future__ import annotations

import copy
import json
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import merge_governor as governor  # noqa: E402
import merge_observation_collect as collector  # noqa: E402


BASE = "1" * 40
HEAD = "2" * 40
BASE_TREE = "3" * 40
HEAD_TREE = "4" * 40
OLD_SCRIPT = "5" * 40
NEW_SCRIPT = "6" * 40
OLD_TEST = "7" * 40
NEW_TEST = "8" * 40


def tree_entry(path: str, mode: str, object_sha: str, kind: str = "blob") -> dict:
    return {"path": path, "mode": mode, "type": kind, "sha": object_sha}


def fixture() -> tuple[dict, dict, dict]:
    policy = json.loads((ROOT / "config" / "merge_governor_policy_v1.json").read_text(encoding="utf-8"))
    workflow = "PolaCore Trusted Task Verification"
    workflow_path = ".github/workflows/trusted-task-verification.yml"
    task = {
        "schema": "polacore.merge-task-manifest/v1",
        "repository": "djibian/polacore",
        "pull_request": 52,
        "source_issue": 51,
        "assurance": "STANDARD",
        "authorized_paths": ["scripts/example.py", "tests/test_example.py"],
        "acceptance_commands": [
            {"command": "python3 -m unittest -v tests/test_example.py", "check": "task-tests"}
        ],
        "checks": [
            {
                "name": "task-tests",
                "kind": "TEST",
                "workflow": workflow,
                "workflow_path": workflow_path,
                "job_name": "task-tests",
            }
        ],
        "verdicts": [
            {
                "role": "REVIEWER",
                "workflow": workflow,
                "workflow_path": workflow_path,
                "job_name": "reviewer",
            }
        ],
    }
    job_suffix = f"/ pr 52 / head {HEAD}"
    snapshot = {
        "schema": "polacore.github-merge-snapshot/v1",
        "repository": "djibian/polacore",
        "pull_request": {
            "number": 52,
            "base": {
                "ref": "engineering",
                "sha": BASE,
                "repo": {"full_name": "djibian/polacore"},
            },
            "head": {"ref": "agent/task-51-example", "sha": HEAD, "repo": {"full_name": "djibian/polacore"}},
            "state": "open",
            "draft": False,
            "mergeable": True,
            "merged": False,
            "merge_commit_sha": None,
        },
        "current_base": {"name": "engineering", "commit": {"sha": BASE}},
        "base_commit": {"sha": BASE, "commit": {"tree": {"sha": BASE_TREE}}},
        "head_commit": {"sha": HEAD, "commit": {"tree": {"sha": HEAD_TREE}}},
        "files": {
            "complete": True,
            "items": [
                {"filename": "scripts/example.py", "status": "modified"},
                {"filename": "tests/test_example.py", "status": "modified"},
            ],
        },
        "base_tree": {
            "sha": BASE_TREE,
            "truncated": False,
            "tree": [
                tree_entry("scripts/example.py", "100644", OLD_SCRIPT),
                tree_entry("tests/test_example.py", "100644", OLD_TEST),
            ],
        },
        "head_tree": {
            "sha": HEAD_TREE,
            "truncated": False,
            "tree": [
                tree_entry("scripts/example.py", "100644", NEW_SCRIPT),
                tree_entry("tests/test_example.py", "100644", NEW_TEST),
            ],
        },
        "workflow_runs": {
            "complete": True,
            "items": [
                {
                    "id": 9001,
                    "name": workflow,
                    "path": workflow_path,
                    "event": "pull_request_target",
                    "head_sha": BASE,
                    "status": "completed",
                    "conclusion": "success",
                    "run_attempt": 1,
                }
            ],
        },
        "jobs": {
            "complete": True,
            "by_run": {
                "9001": {
                    "complete": True,
                    "items": [
                        {"id": 9101, "name": "task-tests " + job_suffix, "status": "completed", "conclusion": "success"},
                        {"id": 9102, "name": "reviewer " + job_suffix, "status": "completed", "conclusion": "success"},
                    ],
                }
            },
        },
        "reviews": {"complete": True, "items": []},
        "review_threads": {"complete": True, "items": []},
    }
    return policy, task, snapshot


def certificate_from(observation: dict) -> dict:
    return {
        key: copy.deepcopy(observation[key])
        for key in governor.CERTIFICATE_KEYS
    } | {"schema": "polacore.merge-certificate/v1"}


class ObservationCollectorTests(unittest.TestCase):
    def assert_collect_rejected(self, mutate) -> None:
        policy, task, snapshot = fixture()
        mutate(policy, task, snapshot)
        with self.assertRaises(governor.Rejected):
            collector.collect(policy, task, snapshot)

    def assert_governor_rejected(self, mutate) -> None:
        policy, task, snapshot = fixture()
        mutate(policy, task, snapshot)
        observation = collector.collect(policy, task, snapshot)
        certificate = certificate_from(observation)
        with self.assertRaises(governor.Rejected):
            governor.evaluate(policy, certificate, observation)

    def test_eligible_authenticated_snapshot_reaches_governor(self) -> None:
        policy, task, snapshot = fixture()
        observation = collector.collect(policy, task, snapshot)
        result = governor.evaluate(policy, certificate_from(observation), observation)
        self.assertEqual(result["decision"], "ELIGIBLE")
        self.assertEqual(observation["head_sha"], HEAD)

    def test_every_paginated_input_must_be_complete(self) -> None:
        for page in ("files", "workflow_runs", "reviews", "review_threads"):
            with self.subTest(page=page):
                self.assert_collect_rejected(lambda _p, _t, s, page=page: s[page].__setitem__("complete", False))
        self.assert_collect_rejected(lambda _p, _t, s: s["jobs"].__setitem__("complete", False))
        self.assert_collect_rejected(
            lambda _p, _t, s: s["jobs"]["by_run"]["9001"].__setitem__("complete", False)
        )

    def test_truncated_git_tree_is_rejected(self) -> None:
        self.assert_collect_rejected(lambda _p, _t, s: s["head_tree"].__setitem__("truncated", True))

    def test_tree_root_must_match_authenticated_commit(self) -> None:
        self.assert_collect_rejected(lambda _p, _t, s: s["head_tree"].__setitem__("sha", "9" * 40))

    def test_omitted_changed_file_is_rejected(self) -> None:
        self.assert_collect_rejected(lambda _p, _t, s: s["files"].__setitem__("items", s["files"]["items"][:1]))

    def test_unchanged_file_reported_modified_is_rejected(self) -> None:
        def mutate(_p, _t, snapshot):
            snapshot["head_tree"]["tree"][0]["sha"] = OLD_SCRIPT

        self.assert_collect_rejected(mutate)

    def test_rename_is_not_normalized(self) -> None:
        def mutate(_p, _t, snapshot):
            snapshot["files"]["items"][0]["status"] = "renamed"
            snapshot["files"]["items"][0]["previous_filename"] = "old.py"

        self.assert_collect_rejected(mutate)

    def test_candidate_controlled_pull_request_workflow_is_rejected(self) -> None:
        def mutate(_p, _t, snapshot):
            run = snapshot["workflow_runs"]["items"][0]
            run["event"] = "pull_request"
            run["head_sha"] = HEAD

        self.assert_collect_rejected(mutate)

    def test_required_workflow_must_be_loaded_from_exact_base(self) -> None:
        self.assert_collect_rejected(
            lambda _p, _t, s: s["workflow_runs"]["items"][0].__setitem__("head_sha", "9" * 40)
        )

    def test_job_name_binds_pr_and_exact_candidate_head(self) -> None:
        self.assert_collect_rejected(
            lambda _p, _t, s: s["jobs"]["by_run"]["9001"]["items"][0].__setitem__("name", "task-tests")
        )

    def test_missing_job_is_rejected(self) -> None:
        self.assert_collect_rejected(lambda _p, _t, s: s["jobs"]["by_run"]["9001"]["items"].pop())

    def test_failed_run_is_rejected(self) -> None:
        self.assert_collect_rejected(
            lambda _p, _t, s: s["workflow_runs"]["items"][0].__setitem__("conclusion", "failure")
        )

    def test_failed_job_is_rejected(self) -> None:
        self.assert_collect_rejected(
            lambda _p, _t, s: s["jobs"]["by_run"]["9001"]["items"][0].__setitem__("conclusion", "skipped")
        )

    def test_duplicate_matching_run_is_ambiguous(self) -> None:
        def mutate(_p, _t, snapshot):
            duplicate = copy.deepcopy(snapshot["workflow_runs"]["items"][0])
            duplicate["id"] = 9002
            snapshot["workflow_runs"]["items"].append(duplicate)
            snapshot["jobs"]["by_run"]["9002"] = copy.deepcopy(snapshot["jobs"]["by_run"]["9001"])
            for job in snapshot["jobs"]["by_run"]["9002"]["items"]:
                job["id"] += 100

        self.assert_collect_rejected(mutate)

    def test_manifest_cannot_reuse_check_job_as_reviewer(self) -> None:
        def mutate(_p, task, _s):
            task["verdicts"][0]["job_name"] = "task-tests"

        self.assert_collect_rejected(mutate)

    def test_manifest_must_cover_assurance_roles(self) -> None:
        def mutate(_p, task, _s):
            task["assurance"] = "REINFORCED"

        self.assert_collect_rejected(mutate)

    def test_current_engineering_movement_is_rejected_by_governor(self) -> None:
        self.assert_governor_rejected(
            lambda _p, _t, s: s["current_base"]["commit"].__setitem__("sha", "9" * 40)
        )

    def test_fork_is_rejected_by_governor(self) -> None:
        self.assert_governor_rejected(
            lambda _p, _t, s: s["pull_request"]["head"]["repo"].__setitem__("full_name", "attacker/polacore")
        )

    def test_base_repository_must_match_policy(self) -> None:
        self.assert_collect_rejected(
            lambda _p, _t, s: s["pull_request"]["base"]["repo"].__setitem__("full_name", "other/polacore")
        )

    def test_draft_is_rejected_by_governor(self) -> None:
        self.assert_governor_rejected(lambda _p, _t, s: s["pull_request"].__setitem__("draft", True))

    def test_closed_unmerged_pull_request_is_rejected(self) -> None:
        self.assert_collect_rejected(lambda _p, _t, s: s["pull_request"].__setitem__("state", "closed"))

    def test_unknown_mergeability_is_rejected_by_governor(self) -> None:
        self.assert_governor_rejected(lambda _p, _t, s: s["pull_request"].__setitem__("mergeable", None))

    def test_integer_mergeability_is_rejected(self) -> None:
        self.assert_collect_rejected(lambda _p, _t, s: s["pull_request"].__setitem__("mergeable", 1))

    def test_unresolved_review_thread_is_rejected_by_governor(self) -> None:
        def mutate(_p, _t, snapshot):
            snapshot["review_threads"]["items"] = [{"isResolved": False}]

        self.assert_governor_rejected(mutate)

    def test_current_head_changes_requested_review_is_contradictory(self) -> None:
        def mutate(_p, _t, snapshot):
            snapshot["reviews"]["items"] = [{"id": 9301, "state": "CHANGES_REQUESTED", "commit_id": HEAD}]

        self.assert_governor_rejected(mutate)

    def test_old_head_changes_requested_review_is_not_replayed(self) -> None:
        policy, task, snapshot = fixture()
        snapshot["reviews"]["items"] = [{"id": 9301, "state": "CHANGES_REQUESTED", "commit_id": "9" * 40}]
        observation = collector.collect(policy, task, snapshot)
        self.assertEqual(observation["contradictory_evidence"], [])

    def test_symlink_mode_is_preserved_then_rejected_by_governor(self) -> None:
        def mutate(_p, _t, snapshot):
            snapshot["head_tree"]["tree"][0]["mode"] = "120000"

        self.assert_governor_rejected(mutate)

    def test_submodule_mode_is_preserved_then_rejected_by_governor(self) -> None:
        def mutate(_p, _t, snapshot):
            entry = snapshot["head_tree"]["tree"][0]
            entry["mode"] = "160000"
            entry["type"] = "commit"

        self.assert_governor_rejected(mutate)

    def test_merged_candidate_requires_separate_replay_record(self) -> None:
        self.assert_collect_rejected(lambda _p, _t, s: s["pull_request"].__setitem__("merged", True))

    def test_unknown_snapshot_authority_key_is_rejected(self) -> None:
        self.assert_collect_rejected(lambda _p, _t, s: s.__setitem__("merge_authorized", True))


if __name__ == "__main__":
    unittest.main()
