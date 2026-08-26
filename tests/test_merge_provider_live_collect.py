from __future__ import annotations

import copy
import datetime as dt
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import merge_governor as governor  # noqa: E402
import merge_provider_live_collect as live  # noqa: E402


NOW = dt.datetime(2026, 8, 26, 12, 45, tzinfo=dt.timezone.utc)


def repository() -> dict:
    return {
        "full_name": "djibian/polacore",
        "owner": {"type": "User"},
        "allow_squash_merge": True,
    }


def ruleset() -> dict:
    return {
        "id": 21296946,
        "name": "Protect engineering",
        "target": "branch",
        "source": "djibian/polacore",
        "source_type": "Repository",
        "enforcement": "active",
        "bypass_actors": [],
        "conditions": {
            "ref_name": {
                "include": ["refs/heads/engineering"],
                "exclude": [],
            }
        },
        "rules": [
            {"type": "deletion"},
            {"type": "non_fast_forward"},
            {
                "type": "pull_request",
                "parameters": {
                    "allowed_merge_methods": ["merge", "squash", "rebase"],
                },
            },
            {
                "type": "required_status_checks",
                "parameters": {
                    "strict_required_status_checks_policy": True,
                    "required_status_checks": [
                        {
                            "context": "deterministic-contract",
                            "integration_id": 15368,
                        }
                    ],
                },
            },
        ],
    }


def fetcher(repo: dict | None = None, rules: dict | None = None):
    payloads = {
        live.REPOSITORY_PATH: repo or repository(),
        live.RULESET_PATH: rules or ruleset(),
    }

    def fetch(path: str):
        return copy.deepcopy(payloads[path]), {"request_id": f"request-{len(path)}"}

    return fetch


class MergeProviderLiveCollectorTests(unittest.TestCase):
    def test_authenticated_snapshot_builds_bounded_unproven_assessment(self) -> None:
        result = live.collect(fetcher(), NOW)
        self.assertEqual(result["schema"], live.LIVE_SCHEMA)
        self.assertEqual(result["observed_at"], "2026-08-26T12:45:00Z")
        self.assertEqual([item["path"] for item in result["requests"]], [
            live.REPOSITORY_PATH,
            live.RULESET_PATH,
        ])
        assessment = result["assessment"]
        self.assertEqual(assessment["selected_operation"], "REST_PULL_MERGE_STRICT_RULESET")
        by_id = {item["id"]: item for item in assessment["operation_assessments"]}
        self.assertEqual(by_id["REST_PULL_MERGE_STRICT_RULESET"]["status"], "ELIGIBLE")
        self.assertEqual(assessment["journal_status"], "UNPROVEN")
        self.assertEqual(assessment["decision"], "UNPROVEN")

    def test_hidden_bypass_actors_fail_closed(self) -> None:
        observed = ruleset()
        del observed["bypass_actors"]
        with self.assertRaisesRegex(governor.Rejected, "hidden"):
            live.collect(fetcher(rules=observed), NOW)

    def test_any_bypass_actor_invalidates_composite(self) -> None:
        observed = ruleset()
        observed["bypass_actors"] = [
            {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}
        ]
        result = live.collect(fetcher(rules=observed), NOW)
        by_id = {
            item["id"]: item
            for item in result["assessment"]["operation_assessments"]
        }
        self.assertEqual(by_id["REST_PULL_MERGE_STRICT_RULESET"]["status"], "UNPROVEN")
        self.assertTrue(result["evidence"]["ruleset"]["current_actor_can_bypass"])

    def test_strict_check_and_latest_base_requirement_are_exact(self) -> None:
        mutations = {
            "not_strict": lambda value: value["rules"][3]["parameters"].__setitem__(
                "strict_required_status_checks_policy", False
            ),
            "wrong_check": lambda value: value["rules"][3]["parameters"].__setitem__(
                "required_status_checks", [{"context": "other"}]
            ),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                observed = ruleset()
                mutate(observed)
                result = live.collect(fetcher(rules=observed), NOW)
                by_id = {
                    item["id"]: item
                    for item in result["assessment"]["operation_assessments"]
                }
                self.assertEqual(
                    by_id["REST_PULL_MERGE_STRICT_RULESET"]["status"], "UNPROVEN"
                )

        observed = ruleset()
        observed["rules"] = observed["rules"][:3]
        with self.assertRaises(governor.Rejected):
            live.collect(fetcher(rules=observed), NOW)

    def test_ruleset_identity_target_and_source_are_fixed(self) -> None:
        mutations = {
            "id": ("id", 1),
            "name": ("name", "attacker"),
            "target": ("target", "tag"),
            "source": ("source", "attacker/polacore"),
            "source_type": ("source_type", "Organization"),
        }
        for name, (key, value) in mutations.items():
            with self.subTest(name=name):
                observed = ruleset()
                observed[key] = value
                with self.assertRaises(governor.Rejected):
                    live.collect(fetcher(rules=observed), NOW)

    def test_engineering_must_be_unambiguously_targeted(self) -> None:
        for include, exclude in [
            (["refs/heads/main"], []),
            (["refs/heads/engineering"], ["refs/heads/engineering"]),
        ]:
            with self.subTest(include=include, exclude=exclude):
                observed = ruleset()
                observed["conditions"]["ref_name"] = {
                    "include": include,
                    "exclude": exclude,
                }
                with self.assertRaises(governor.Rejected):
                    live.collect(fetcher(rules=observed), NOW)

    def test_duplicate_security_rules_and_checks_are_rejected(self) -> None:
        observed = ruleset()
        observed["rules"].append(copy.deepcopy(observed["rules"][3]))
        with self.assertRaisesRegex(governor.Rejected, "duplicate"):
            live.collect(fetcher(rules=observed), NOW)

        observed = ruleset()
        observed["rules"][3]["parameters"]["required_status_checks"].append(
            {"context": "deterministic-contract"}
        )
        with self.assertRaisesRegex(governor.Rejected, "duplicate"):
            live.collect(fetcher(rules=observed), NOW)

    def test_repository_identity_owner_and_squash_are_fixed(self) -> None:
        cases = [
            {"full_name": "attacker/polacore"},
            {"owner": {"type": "Unknown"}},
            {"allow_squash_merge": False},
        ]
        for mutation in cases:
            with self.subTest(mutation=mutation):
                repo = repository()
                repo.update(mutation)
                with self.assertRaises(governor.Rejected):
                    live.collect(fetcher(repo=repo), NOW)

    def test_request_ids_and_timezone_are_mandatory(self) -> None:
        def no_id(path: str):
            payload = repository() if path == live.REPOSITORY_PATH else ruleset()
            return payload, {}

        with self.assertRaises(governor.Rejected):
            live.collect(no_id, NOW)
        with self.assertRaises(governor.Rejected):
            live.collect(fetcher(), dt.datetime(2026, 8, 26, 12, 45))

    def test_http_client_requires_token_and_endpoint_allowlist(self) -> None:
        with self.assertRaises(governor.Rejected):
            live.GitHubGetClient("")
        client = live.GitHubGetClient("not-a-real-token", opener=object())
        with self.assertRaisesRegex(governor.Rejected, "allowlist"):
            client.fetch("/user")

    def test_evidence_and_assessment_are_deterministic_for_fixed_inputs(self) -> None:
        first = live.collect(fetcher(), NOW)
        second = live.collect(fetcher(), NOW)
        self.assertEqual(first, second)
        later = live.collect(fetcher(), NOW + dt.timedelta(seconds=1))
        self.assertEqual(first["evidence"], later["evidence"])
        self.assertNotEqual(first["observed_at"], later["observed_at"])


if __name__ == "__main__":
    unittest.main()
