from __future__ import annotations

import copy
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import merge_certificate_build as certificate_builder  # noqa: E402
import merge_controller_protocol as controller  # noqa: E402
import merge_decision_bundle as bundler  # noqa: E402
import merge_governor as governor  # noqa: E402
import merge_observation_collect as collector  # noqa: E402
from tests.test_merge_observation_collect import fixture as observation_fixture  # noqa: E402


CLAIM_FIELDS = {
    "repository", "pull_request", "base_ref", "base_sha", "head_repo",
    "head_ref", "head_sha", "changes", "checks", "verdicts",
}
MERGE_SHA = "9" * 40
MOVED_SHA = "a" * 40


def fixture() -> tuple[dict, dict]:
    policy, manifest, snapshot = observation_fixture()
    observation = collector.collect(policy, manifest, snapshot)
    claims = {key: copy.deepcopy(observation[key]) for key in CLAIM_FIELDS}
    claims["schema"] = certificate_builder.CLAIMS_SCHEMA
    return policy, bundler.build_bundle(policy, manifest, claims, snapshot)


def live_state(bundle: dict, *, state: str = "OPEN") -> dict:
    certificate = bundle["certificate"]
    merged = state == "MERGED"
    return {
        "schema": controller.LIVE_STATE_SCHEMA,
        "repository": bundle["intent"]["repository"],
        "pull_request": bundle["intent"]["pull_request"],
        "base_ref": bundle["intent"]["target_ref"],
        "current_target_sha": MERGE_SHA if merged else bundle["intent"]["base_sha"],
        "head_repo": certificate["head_repo"],
        "head_ref": certificate["head_ref"],
        "head_sha": bundle["intent"]["head_sha"],
        "state": state,
        "draft": False,
        "mergeable": False if merged else True,
        "merged": merged,
        "merge_sha": MERGE_SHA if merged else None,
        "protection_bypass_requested": False,
    }


class FakeAdapter:
    def __init__(self, state: dict):
        self.state = copy.deepcopy(state)
        self.journal = None
        self.events: list[str] = []
        self.cas_status = "APPLIED"
        self.cas_merge_sha = MERGE_SHA
        self.prepare_persists = True
        self.prepare_raises = False
        self.complete_persists = True
        self.complete_raises = False
        self.cas_raises = False
        self.after_cas_state: dict | None = None
        self.last_request: dict | None = None

    def read_state(self, repository: str, pull_request: int) -> dict:
        self.events.append("read_state")
        return copy.deepcopy(self.state)

    def read_journal(self, binding: str) -> dict | None:
        self.events.append("read_journal")
        return copy.deepcopy(self.journal)

    def prepare(self, entry: dict) -> None:
        self.events.append("prepare")
        if self.prepare_persists:
            self.journal = copy.deepcopy(entry)
        if self.prepare_raises:
            raise controller.AdapterError("uncertain prepare")

    def merge_squash_compare_and_swap(self, request: dict) -> dict:
        self.events.append("cas")
        self.last_request = copy.deepcopy(request)
        if self.after_cas_state is not None:
            self.state = copy.deepcopy(self.after_cas_state)
        elif self.cas_status == "APPLIED":
            self.state.update(
                {
                    "state": "MERGED", "merged": True, "mergeable": False,
                    "merge_sha": self.cas_merge_sha, "current_target_sha": self.cas_merge_sha,
                }
            )
        if self.cas_raises:
            raise controller.AdapterError("uncertain merge")
        return {
            "schema": controller.CAS_RESULT_SCHEMA,
            "status": self.cas_status,
            "repository": request["repository"],
            "pull_request": request["pull_request"],
            "expected_base_sha": request["expected_base_sha"],
            "expected_head_sha": request["expected_head_sha"],
            "merge_sha": self.cas_merge_sha if self.cas_status == "APPLIED" else None,
        }

    def complete(self, entry: dict) -> None:
        self.events.append("complete")
        if self.complete_persists:
            self.journal = copy.deepcopy(entry)
        if self.complete_raises:
            raise controller.AdapterError("uncertain complete")


class MergeControllerProtocolTests(unittest.TestCase):
    def test_success_uses_one_cas_after_durable_prepare(self) -> None:
        policy, bundle = fixture()
        adapter = FakeAdapter(live_state(bundle))
        result = controller.execute(policy, bundle, adapter)
        self.assertEqual(result["status"], "MERGED_RECORDED")
        self.assertEqual(result["merge_sha"], MERGE_SHA)
        self.assertEqual(adapter.events.count("cas"), 1)
        self.assertLess(adapter.events.index("prepare"), adapter.events.index("cas"))
        self.assertEqual(adapter.last_request["expected_base_sha"], bundle["intent"]["base_sha"])
        self.assertEqual(adapter.last_request["expected_head_sha"], bundle["intent"]["head_sha"])
        self.assertEqual(adapter.last_request["bundle_binding_sha256"], bundle["binding_sha256"])
        self.assertEqual(adapter.journal["state"], "COMPLETED")
        self.assertEqual(adapter.journal["completion_kind"], "CAS_CONFIRMED")

    def test_second_invocation_is_idempotent(self) -> None:
        policy, bundle = fixture()
        adapter = FakeAdapter(live_state(bundle))
        controller.execute(policy, bundle, adapter)
        result = controller.execute(policy, bundle, adapter)
        self.assertEqual(result["status"], "ALREADY_RECORDED")
        self.assertEqual(adapter.events.count("cas"), 1)

    def test_stale_base_stops_before_prepare(self) -> None:
        policy, bundle = fixture()
        state = live_state(bundle)
        state["current_target_sha"] = MOVED_SHA
        adapter = FakeAdapter(state)
        result = controller.execute(policy, bundle, adapter)
        self.assertEqual(result["status"], "STOP_STALE")
        self.assertNotIn("prepare", adapter.events)
        self.assertNotIn("cas", adapter.events)

    def test_stale_head_stops_before_prepare(self) -> None:
        policy, bundle = fixture()
        state = live_state(bundle)
        state["head_sha"] = MOVED_SHA
        adapter = FakeAdapter(state)
        result = controller.execute(policy, bundle, adapter)
        self.assertEqual(result["status"], "STOP_STALE")
        self.assertNotIn("cas", adapter.events)

    def test_non_mergeable_open_state_stops(self) -> None:
        policy, bundle = fixture()
        state = live_state(bundle)
        state["mergeable"] = None
        adapter = FakeAdapter(state)
        self.assertEqual(controller.execute(policy, bundle, adapter)["status"], "STOP_STALE")
        self.assertNotIn("cas", adapter.events)

    def test_draft_fork_main_and_bypass_are_rejected(self) -> None:
        policy, bundle = fixture()
        mutations = {
            "draft": lambda state: state.__setitem__("draft", True),
            "fork": lambda state: state.__setitem__("head_repo", "attacker/polacore"),
            "main": lambda state: state.__setitem__("base_ref", "main"),
            "bypass": lambda state: state.__setitem__("protection_bypass_requested", True),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                state = live_state(bundle)
                mutate(state)
                adapter = FakeAdapter(state)
                with self.assertRaises(governor.Rejected):
                    controller.execute(policy, bundle, adapter)
                self.assertNotIn("cas", adapter.events)

    def test_prepare_must_be_durably_confirmed(self) -> None:
        policy, bundle = fixture()
        adapter = FakeAdapter(live_state(bundle))
        adapter.prepare_persists = False
        result = controller.execute(policy, bundle, adapter)
        self.assertEqual(result["status"], "RETRY_REQUIRED")
        self.assertNotIn("cas", adapter.events)

    def test_uncertain_prepare_may_continue_only_if_persisted(self) -> None:
        policy, bundle = fixture()
        adapter = FakeAdapter(live_state(bundle))
        adapter.prepare_raises = True
        result = controller.execute(policy, bundle, adapter)
        self.assertEqual(result["status"], "MERGED_RECORDED")
        self.assertEqual(adapter.events.count("cas"), 1)

    def test_atomic_cas_rejects_race_without_retrying(self) -> None:
        policy, bundle = fixture()
        adapter = FakeAdapter(live_state(bundle))
        adapter.cas_status = "STALE"
        result = controller.execute(policy, bundle, adapter)
        self.assertEqual(result["status"], "STOP_STALE")
        self.assertEqual(adapter.events.count("cas"), 1)
        self.assertNotIn("complete", adapter.events)

    def test_uncertain_merge_recovers_from_fresh_merged_state(self) -> None:
        policy, bundle = fixture()
        adapter = FakeAdapter(live_state(bundle))
        adapter.cas_raises = True
        result = controller.execute(policy, bundle, adapter)
        self.assertEqual(result["status"], "RECOVERED_RECORDED")
        self.assertEqual(adapter.journal["completion_kind"], "OBSERVED_AFTER_PREPARE")
        self.assertEqual(adapter.events.count("cas"), 1)

    def test_uncertain_merge_open_state_requires_later_retry(self) -> None:
        policy, bundle = fixture()
        adapter = FakeAdapter(live_state(bundle))
        adapter.cas_status = "UNCERTAIN"
        result = controller.execute(policy, bundle, adapter)
        self.assertEqual(result["status"], "RETRY_REQUIRED")
        self.assertEqual(adapter.events.count("cas"), 1)
        self.assertEqual(adapter.journal["state"], "PREPARED")

    def test_applied_response_without_observed_merge_is_not_trusted(self) -> None:
        policy, bundle = fixture()
        adapter = FakeAdapter(live_state(bundle))
        adapter.after_cas_state = live_state(bundle)
        result = controller.execute(policy, bundle, adapter)
        self.assertEqual(result["status"], "MERGE_OUTCOME_UNCONFIRMED")
        self.assertEqual(adapter.journal["state"], "PREPARED")

    def test_race_after_prepare_stops_on_changed_fresh_state(self) -> None:
        policy, bundle = fixture()
        adapter = FakeAdapter(live_state(bundle))
        changed = live_state(bundle)
        changed["head_sha"] = MOVED_SHA
        adapter.cas_status = "UNCERTAIN"
        adapter.after_cas_state = changed
        result = controller.execute(policy, bundle, adapter)
        self.assertEqual(result["status"], "STOP_STALE")
        self.assertNotIn("complete", adapter.events)

    def test_prepared_crash_recovery_does_not_issue_second_merge(self) -> None:
        policy, bundle = fixture()
        adapter = FakeAdapter(live_state(bundle, state="MERGED"))
        adapter.journal = controller.expected_journal(bundle)
        result = controller.execute(policy, bundle, adapter)
        self.assertEqual(result["status"], "RECOVERED_RECORDED")
        self.assertNotIn("cas", adapter.events)
        self.assertEqual(adapter.journal["merge_sha"], MERGE_SHA)

    def test_merged_without_prepared_intent_is_unproven(self) -> None:
        policy, bundle = fixture()
        adapter = FakeAdapter(live_state(bundle, state="MERGED"))
        with self.assertRaises(governor.Rejected):
            controller.execute(policy, bundle, adapter)
        self.assertNotIn("complete", adapter.events)
        self.assertNotIn("cas", adapter.events)

    def test_complete_must_be_durably_confirmed(self) -> None:
        policy, bundle = fixture()
        adapter = FakeAdapter(live_state(bundle))
        adapter.complete_persists = False
        result = controller.execute(policy, bundle, adapter)
        self.assertEqual(result["status"], "MERGED_RECORD_UNCONFIRMED")
        self.assertEqual(adapter.events.count("cas"), 1)
        self.assertEqual(adapter.journal["state"], "PREPARED")

    def test_uncertain_complete_succeeds_only_if_persisted(self) -> None:
        policy, bundle = fixture()
        adapter = FakeAdapter(live_state(bundle))
        adapter.complete_raises = True
        result = controller.execute(policy, bundle, adapter)
        self.assertEqual(result["status"], "MERGED_RECORDED")
        self.assertEqual(adapter.journal["state"], "COMPLETED")

    def test_mismatched_journal_never_reaches_merge(self) -> None:
        policy, bundle = fixture()
        adapter = FakeAdapter(live_state(bundle))
        adapter.journal = controller.expected_journal(bundle)
        adapter.journal["head_sha"] = MOVED_SHA
        with self.assertRaises(governor.Rejected):
            controller.execute(policy, bundle, adapter)
        self.assertNotIn("cas", adapter.events)

    def test_cas_result_identity_and_merge_sha_are_verified(self) -> None:
        policy, bundle = fixture()
        adapter = FakeAdapter(live_state(bundle))
        adapter.cas_merge_sha = MOVED_SHA
        adapter.after_cas_state = live_state(bundle, state="MERGED")
        with self.assertRaises(governor.Rejected):
            controller.execute(policy, bundle, adapter)
        self.assertNotIn("complete", adapter.events)

    def test_replay_bundle_never_writes_or_merges(self) -> None:
        policy, open_bundle = fixture()
        observation = copy.deepcopy(open_bundle["observation"])
        observation["current_engineering_sha"] = MERGE_SHA
        observation["mergeable"] = False
        observation["merge"] = {
            "state": "MERGED",
            "head_sha": open_bundle["intent"]["head_sha"],
            "merge_sha": MERGE_SHA,
            "certificate_sha256": open_bundle["certificate_sha256"],
        }
        decision = governor.evaluate(policy, open_bundle["certificate"], observation)
        intent = bundler.build_intent(policy, open_bundle["certificate"], observation, decision)
        replay = {
            "schema": bundler.BUNDLE_SCHEMA,
            "certificate": open_bundle["certificate"],
            "certificate_sha256": open_bundle["certificate_sha256"],
            "observation": observation,
            "observation_sha256": governor.digest(observation),
            "decision": decision,
            "decision_sha256": governor.digest(decision),
            "intent": intent,
            "intent_sha256": governor.digest(intent),
            "binding_sha256": "",
        }
        replay["binding_sha256"] = governor.digest(bundler.binding_payload(replay))
        bundler.verify_bundle(policy, replay)
        adapter = FakeAdapter(live_state(replay, state="MERGED"))
        result = controller.execute(policy, replay, adapter)
        self.assertEqual(result["status"], "NO_ACTION_ALREADY_MERGED")
        self.assertNotIn("prepare", adapter.events)
        self.assertNotIn("cas", adapter.events)
        self.assertNotIn("complete", adapter.events)

    def test_unknown_live_or_cas_fields_fail_closed(self) -> None:
        policy, bundle = fixture()
        state = live_state(bundle)
        state["merge_authorized"] = True
        with self.assertRaises(governor.Rejected):
            controller.execute(policy, bundle, FakeAdapter(state))

        adapter = FakeAdapter(live_state(bundle))
        original = adapter.merge_squash_compare_and_swap

        def tampered(request):
            result = original(request)
            result["authorized"] = True
            return result

        adapter.merge_squash_compare_and_swap = tampered
        with self.assertRaises(governor.Rejected):
            controller.execute(policy, bundle, adapter)

    def test_malformed_applied_result_recovers_without_a_second_merge(self) -> None:
        policy, bundle = fixture()
        adapter = FakeAdapter(live_state(bundle))
        original = adapter.merge_squash_compare_and_swap

        def malformed(request):
            result = original(request)
            result["authorization"] = "untrusted"
            return result

        adapter.merge_squash_compare_and_swap = malformed
        with self.assertRaises(governor.Rejected):
            controller.execute(policy, bundle, adapter)
        self.assertEqual(adapter.events.count("cas"), 1)
        self.assertEqual(adapter.journal["state"], "PREPARED")

        adapter.merge_squash_compare_and_swap = original
        result = controller.execute(policy, bundle, adapter)
        self.assertEqual(result["status"], "RECOVERED_RECORDED")
        self.assertEqual(adapter.events.count("cas"), 1)
        self.assertEqual(adapter.journal["completion_kind"], "OBSERVED_AFTER_PREPARE")

    def test_adapter_cannot_mutate_the_expected_request_used_for_validation(self) -> None:
        policy, bundle = fixture()
        adapter = FakeAdapter(live_state(bundle))

        def mutated_request(request):
            adapter.events.append("cas")
            request["expected_head_sha"] = MOVED_SHA
            return {
                "schema": controller.CAS_RESULT_SCHEMA,
                "status": "UNCERTAIN",
                "repository": request["repository"],
                "pull_request": request["pull_request"],
                "expected_base_sha": request["expected_base_sha"],
                "expected_head_sha": request["expected_head_sha"],
                "merge_sha": None,
            }

        adapter.merge_squash_compare_and_swap = mutated_request
        with self.assertRaises(governor.Rejected):
            controller.execute(policy, bundle, adapter)

    def test_stale_policy_rejects_before_adapter_access(self) -> None:
        policy, bundle = fixture()
        policy["version"] = "stale"
        adapter = FakeAdapter(live_state(bundle))
        with self.assertRaises(governor.Rejected):
            controller.execute(policy, bundle, adapter)
        self.assertEqual(adapter.events, [])


if __name__ == "__main__":
    unittest.main()
