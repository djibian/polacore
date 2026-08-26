from __future__ import annotations

import copy
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import merge_governor as governor  # noqa: E402
import merge_provider_capability as capability  # noqa: E402


FIXTURE = ROOT / "tests" / "fixtures" / "merge_provider_github_2026-08-25.json"


def fixture() -> dict:
    return governor.load_json(FIXTURE)


class MergeProviderCapabilityTests(unittest.TestCase):
    def test_observed_github_profile_is_unproven(self) -> None:
        result = capability.assess(fixture())
        self.assertEqual(result["decision"], "UNPROVEN")
        self.assertEqual(result["selected_operation"], "REST_PULL_MERGE_STRICT_RULESET")
        by_id = {item["id"]: item for item in result["operation_assessments"]}
        self.assertEqual(by_id["REST_PULL_MERGE_STRICT_RULESET"]["status"], "ELIGIBLE")
        self.assertIn(
            "base_precondition=NONE requires EXACT_BASE or STRICT_REQUIRED_STATUS",
            by_id["REST_PULL_MERGE"]["reasons"],
        )
        self.assertIn(
            "base_precondition=FAST_FORWARD_ONLY requires EXACT_BASE or STRICT_REQUIRED_STATUS",
            by_id["REST_GIT_REF_UPDATE"]["reasons"],
        )
        self.assertIn("availability=UNAVAILABLE requires AVAILABLE", by_id["GITHUB_MERGE_QUEUE"]["reasons"])
        self.assertEqual(result["journal_status"], "UNPROVEN")
        self.assertEqual(
            result["reasons"],
            capability.journal_reasons(fixture()["journal"]),
        )

    def test_requirement_predicates_have_a_positive_shape(self) -> None:
        self.assertEqual(capability.operation_reasons(capability.REQUIRED_OPERATION), [])
        self.assertEqual(capability.journal_reasons(capability.REQUIRED_JOURNAL), [])

    def test_head_only_operation_never_substitutes_for_base_cas(self) -> None:
        evidence = fixture()
        evidence["selected_operation"] = "REST_PULL_MERGE"
        result = capability.assess(evidence)
        self.assertEqual(result["decision"], "UNPROVEN")
        self.assertIn("base_precondition=NONE requires EXACT_BASE or STRICT_REQUIRED_STATUS", result["reasons"])

    def test_fast_forward_is_not_claimed_as_exact_base_cas(self) -> None:
        evidence = fixture()
        evidence["selected_operation"] = "REST_GIT_REF_UPDATE"
        result = capability.assess(evidence)
        self.assertEqual(result["decision"], "UNPROVEN")
        self.assertIn("base_precondition=FAST_FORWARD_ONLY requires EXACT_BASE or STRICT_REQUIRED_STATUS", result["reasons"])

    def test_latest_base_queue_changes_the_certificate_contract(self) -> None:
        evidence = fixture()
        evidence["selected_operation"] = "GITHUB_MERGE_QUEUE"
        result = capability.assess(evidence)
        self.assertEqual(result["decision"], "UNPROVEN")
        self.assertIn("base_precondition=LATEST_BASE requires EXACT_BASE or STRICT_REQUIRED_STATUS", result["reasons"])

    def test_operation_must_bind_exact_pr_and_head(self) -> None:
        evidence = fixture()
        evidence["selected_operation"] = "REST_GIT_REF_UPDATE"
        result = capability.assess(evidence)
        self.assertIn("pull_request_precondition=NONE requires EXACT_PR", result["reasons"])
        self.assertIn("head_precondition=NONE requires EXACT_HEAD", result["reasons"])

    def test_strict_ruleset_composite_is_bounded_not_exact_base_cas(self) -> None:
        evidence = fixture()
        operation = next(
            item for item in evidence["operations"]
            if item["id"] == "REST_PULL_MERGE_STRICT_RULESET"
        )
        self.assertEqual(operation["base_precondition"], "STRICT_REQUIRED_STATUS")
        result = capability.assess(evidence)
        by_id = {item["id"]: item for item in result["operation_assessments"]}
        self.assertEqual(by_id[operation["id"]]["status"], "ELIGIBLE")
        self.assertEqual(result["decision"], "UNPROVEN")
        self.assertEqual(result["journal_status"], "UNPROVEN")

    def test_strict_ruleset_properties_are_all_mandatory(self) -> None:
        mutations = {
            "not_strict": lambda rules: rules.__setitem__("strict_required_status", False),
            "not_up_to_date": lambda rules: rules.__setitem__("required_branch_up_to_date", False),
            "wrong_check": lambda rules: rules.__setitem__("required_status_checks", ["other"]),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                evidence = fixture()
                mutate(evidence["ruleset"])
                result = capability.assess(evidence)
                self.assertEqual(result["decision"], "UNPROVEN")
                by_id = {item["id"]: item for item in result["operation_assessments"]}
                self.assertEqual(
                    by_id["REST_PULL_MERGE_STRICT_RULESET"]["status"], "UNPROVEN"
                )

    def test_bypass_or_inactive_ruleset_blocks_every_operation(self) -> None:
        mutations = {
            "bypass": lambda rules: rules.__setitem__("current_actor_can_bypass", True),
            "bypass_actor": lambda rules: rules.__setitem__("bypass_actor_count", 1),
            "inactive": lambda rules: rules.__setitem__("enforcement", "DISABLED"),
            "no_pr": lambda rules: rules.__setitem__("pull_request_required", False),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                evidence = fixture()
                evidence["selected_operation"] = "REST_PULL_MERGE_STRICT_RULESET"
                mutate(evidence["ruleset"])
                self.assertEqual(capability.assess(evidence)["decision"], "UNPROVEN")

    def test_required_squash_cannot_be_silently_changed(self) -> None:
        evidence = fixture()
        evidence["required_merge_method"] = "MERGE"
        with self.assertRaises(governor.Rejected):
            capability.assess(evidence)

        evidence = fixture()
        evidence["operations"][0]["merge_method"] = "MERGE"
        with self.assertRaises(governor.Rejected):
            capability.assess(evidence)

    def test_durable_monotonic_exact_journal_is_mandatory(self) -> None:
        evidence = fixture()
        result = capability.assess(evidence)
        self.assertEqual(result["journal_status"], "UNPROVEN")
        self.assertIn("journal.availability=UNAVAILABLE requires AVAILABLE", result["reasons"])

    def test_input_cannot_self_promote_operation_or_journal(self) -> None:
        evidence = fixture()
        evidence["operations"][0]["base_precondition"] = "EXACT_BASE"
        with self.assertRaises(governor.Rejected):
            capability.assess(evidence)

        evidence = fixture()
        evidence["journal"].update(capability.REQUIRED_JOURNAL)
        with self.assertRaises(governor.Rejected):
            capability.assess(evidence)

    def test_selected_operation_must_exist(self) -> None:
        evidence = fixture()
        evidence["selected_operation"] = "UNKNOWN_OPERATION"
        with self.assertRaises(governor.Rejected):
            capability.assess(evidence)

    def test_duplicate_operation_or_source_ids_are_rejected(self) -> None:
        evidence = fixture()
        evidence["operations"].append(copy.deepcopy(evidence["operations"][0]))
        with self.assertRaises(governor.Rejected):
            capability.assess(evidence)

        evidence = fixture()
        evidence["sources"].append(copy.deepcopy(evidence["sources"][0]))
        with self.assertRaises(governor.Rejected):
            capability.assess(evidence)

    def test_unknown_or_non_primary_sources_are_rejected(self) -> None:
        evidence = fixture()
        evidence["operations"][0]["source_ids"] = ["MISSING"]
        with self.assertRaises(governor.Rejected):
            capability.assess(evidence)

        evidence = fixture()
        evidence["sources"][0]["url"] = "https://example.com/blog"
        with self.assertRaises(governor.Rejected):
            capability.assess(evidence)

        evidence = fixture()
        canary = next(
            source for source in evidence["sources"]
            if source["id"] == "POLACORE_STRICT_BASE_CANARY"
        )
        canary["supports"].remove("BOUNDED_CANARY_ONLY")
        with self.assertRaises(governor.Rejected):
            capability.assess(evidence)

    def test_unknown_fields_fail_closed(self) -> None:
        evidence = fixture()
        evidence["authorized"] = True
        with self.assertRaises(governor.Rejected):
            capability.assess(evidence)

        evidence = fixture()
        evidence["operations"][0]["expected_base"] = True
        with self.assertRaises(governor.Rejected):
            capability.assess(evidence)

    def test_repository_provider_and_target_are_fixed(self) -> None:
        mutations = {
            "provider": ("provider", "OTHER"),
            "repository": ("repository", "attacker/polacore"),
            "target": ("target_ref", "main"),
        }
        for name, (key, value) in mutations.items():
            with self.subTest(name=name):
                evidence = fixture()
                evidence[key] = value
                with self.assertRaises(governor.Rejected):
                    capability.assess(evidence)

    def test_assessment_is_deterministic_and_digest_bound(self) -> None:
        evidence = fixture()
        first = capability.assess(evidence)
        second = capability.assess(copy.deepcopy(evidence))
        self.assertEqual(first, second)
        evidence["observed_at"] = "2026-08-27"
        self.assertNotEqual(first["evidence_sha256"], capability.assess(evidence)["evidence_sha256"])


if __name__ == "__main__":
    unittest.main()
