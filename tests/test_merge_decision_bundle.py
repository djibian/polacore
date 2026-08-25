from __future__ import annotations

import copy
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import merge_certificate_build as certificate_builder  # noqa: E402
import merge_decision_bundle as bundler  # noqa: E402
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
MERGE_SHA = "9" * 40


def fixture() -> tuple[dict, dict, dict, dict]:
    policy, manifest, snapshot = observation_fixture()
    observation = collector.collect(policy, manifest, snapshot)
    claims = {key: copy.deepcopy(observation[key]) for key in CLAIM_FIELDS}
    claims["schema"] = certificate_builder.CLAIMS_SCHEMA
    return policy, manifest, claims, snapshot


class MergeDecisionBundleTests(unittest.TestCase):
    def test_eligible_bundle_proposes_only_fresh_compare_and_swap(self) -> None:
        policy, manifest, claims, snapshot = fixture()
        bundle = bundler.build_bundle(policy, manifest, claims, snapshot)
        self.assertEqual(bundle["decision"]["decision"], "ELIGIBLE")
        self.assertEqual(bundle["intent"]["disposition"], "PROPOSE_MERGE")
        self.assertTrue(bundle["intent"]["fresh_compare_and_swap_required"])
        self.assertEqual(bundle["intent"]["merge_method"], "squash")
        self.assertIsNone(bundle["intent"]["recorded_merge_sha"])
        self.assertEqual(bundle["intent"]["observation_sha256"], bundle["observation_sha256"])
        self.assertIs(bundler.verify_bundle(policy, bundle), bundle)

    def test_bundle_is_deterministic_for_identical_inputs(self) -> None:
        policy, manifest, claims, snapshot = fixture()
        first = bundler.build_bundle(policy, manifest, claims, snapshot)
        second = bundler.build_bundle(policy, manifest, claims, snapshot)
        self.assertEqual(first, second)

    def test_claim_and_observation_divergence_is_rejected(self) -> None:
        policy, manifest, claims, snapshot = fixture()
        claims["checks"][0]["run_id"] += 100
        with self.assertRaises(governor.Rejected):
            bundler.build_bundle(policy, manifest, claims, snapshot)

    def test_engineering_movement_produces_no_bundle(self) -> None:
        policy, manifest, claims, snapshot = fixture()
        snapshot["current_base"]["commit"]["sha"] = MERGE_SHA
        with self.assertRaises(governor.Rejected):
            bundler.build_bundle(policy, manifest, claims, snapshot)

    def test_every_embedded_artifact_is_digest_bound(self) -> None:
        policy, manifest, claims, snapshot = fixture()
        original = bundler.build_bundle(policy, manifest, claims, snapshot)
        mutations = {
            "certificate": lambda b: b["certificate"].__setitem__("pull_request", 999),
            "observation": lambda b: b["observation"].__setitem__("pull_request", 999),
            "decision": lambda b: b["decision"].__setitem__("pull_request", 999),
            "intent": lambda b: b["intent"].__setitem__("pull_request", 999),
            "binding": lambda b: b.__setitem__("binding_sha256", "sha256:" + "0" * 64),
        }
        for name, mutate in mutations.items():
            with self.subTest(artifact=name):
                candidate = copy.deepcopy(original)
                mutate(candidate)
                with self.assertRaises(governor.Rejected):
                    bundler.verify_bundle(policy, candidate)

    def test_stale_policy_cannot_verify_old_bundle(self) -> None:
        policy, manifest, claims, snapshot = fixture()
        bundle = bundler.build_bundle(policy, manifest, claims, snapshot)
        policy["version"] = "2026-08-25.stale"
        with self.assertRaises(governor.Rejected):
            bundler.verify_bundle(policy, bundle)

    def test_exact_merged_replay_emits_no_action(self) -> None:
        policy, manifest, claims, snapshot = fixture()
        open_bundle = bundler.build_bundle(policy, manifest, claims, snapshot)
        snapshot["pull_request"].update(
            {"state": "closed", "merged": True, "mergeable": False, "merge_commit_sha": MERGE_SHA}
        )
        snapshot["current_base"]["commit"]["sha"] = MERGE_SHA
        snapshot["merge_record"] = {
            "head_sha": claims["head_sha"],
            "merge_sha": MERGE_SHA,
            "certificate_sha256": open_bundle["certificate_sha256"],
        }

        replay = bundler.build_bundle(policy, manifest, claims, snapshot)
        self.assertEqual(replay["decision"]["decision"], "ALREADY_MERGED")
        self.assertEqual(replay["intent"]["disposition"], "NO_ACTION_ALREADY_MERGED")
        self.assertFalse(replay["intent"]["fresh_compare_and_swap_required"])
        self.assertIsNone(replay["intent"]["merge_method"])
        self.assertEqual(replay["intent"]["recorded_merge_sha"], MERGE_SHA)

    def test_replay_with_another_certificate_digest_is_rejected(self) -> None:
        policy, manifest, claims, snapshot = fixture()
        snapshot["pull_request"].update(
            {"state": "closed", "merged": True, "mergeable": False, "merge_commit_sha": MERGE_SHA}
        )
        snapshot["current_base"]["commit"]["sha"] = MERGE_SHA
        snapshot["merge_record"] = {
            "head_sha": claims["head_sha"],
            "merge_sha": MERGE_SHA,
            "certificate_sha256": "sha256:" + "0" * 64,
        }
        with self.assertRaises(governor.Rejected):
            bundler.build_bundle(policy, manifest, claims, snapshot)

    def test_unknown_bundle_or_intent_fields_are_rejected(self) -> None:
        policy, manifest, claims, snapshot = fixture()
        bundle = bundler.build_bundle(policy, manifest, claims, snapshot)
        bundle["merge_authorized"] = True
        with self.assertRaises(governor.Rejected):
            bundler.verify_bundle(policy, bundle)

        bundle = bundler.build_bundle(policy, manifest, claims, snapshot)
        bundle["intent"]["authorized"] = True
        with self.assertRaises(governor.Rejected):
            bundler.verify_bundle(policy, bundle)


if __name__ == "__main__":
    unittest.main()
