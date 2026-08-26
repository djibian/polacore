#!/usr/bin/env python3
"""Pure fail-closed assessment of a prospective merge provider capability.

The evidence consumed here must be assembled by trusted-base code from primary
sources.  This module does not fetch those sources, hold credentials, select a
provider endpoint, write a journal, publish, or merge.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

import merge_governor as governor


EVIDENCE_SCHEMA = "polacore.merge-provider-capability-evidence/v1"
ASSESSMENT_SCHEMA = "polacore.merge-provider-capability-assessment/v1"

EVIDENCE_KEYS = {
    "schema",
    "provider",
    "repository",
    "repository_owner_type",
    "target_ref",
    "required_merge_method",
    "observed_at",
    "ruleset",
    "operations",
    "journal",
    "selected_operation",
    "sources",
}
RULESET_KEYS = {
    "id",
    "enforcement",
    "pull_request_required",
    "non_fast_forward_forbidden",
    "deletion_forbidden",
    "merge_queue_required",
    "bypass_actor_count",
    "current_actor_can_bypass",
    "allowed_merge_methods",
    "required_status_checks",
    "strict_required_status",
    "required_branch_up_to_date",
    "source_ids",
}
OPERATION_KEYS = {
    "id",
    "availability",
    "pull_request_precondition",
    "head_precondition",
    "base_precondition",
    "protection_behavior",
    "merge_method",
    "audit_behavior",
    "outcome_recovery",
    "source_ids",
}
JOURNAL_KEYS = {
    "id",
    "availability",
    "binding",
    "monotonicity",
    "durability",
    "retention",
    "candidate_write_access",
    "source_ids",
}
SOURCE_KEYS = {"id", "kind", "url", "retrieved_on", "supports"}

REQUIRED_OPERATION = {
    "availability": "AVAILABLE",
    "pull_request_precondition": "EXACT_PR",
    "head_precondition": "EXACT_HEAD",
    "base_precondition": "EXACT_BASE",
    "protection_behavior": "RESPECTS_WITHOUT_BYPASS",
    "merge_method": "SQUASH",
    "audit_behavior": "PR_MERGED_EXACT_SHA",
    "outcome_recovery": "FRESH_STATE_RECOVERABLE",
}
REQUIRED_JOURNAL = {
    "availability": "AVAILABLE",
    "binding": "EXACT_BUNDLE",
    "monotonicity": "PREPARED_TO_COMPLETED_ONLY",
    "durability": "DURABLE",
    "retention": "INDEFINITE",
    "candidate_write_access": False,
}

# These contracts are trusted-base findings, not claims supplied by the input.
# Adding or strengthening a profile requires a separately reviewed code change.
KNOWN_OPERATION_CONTRACTS = {
    "REST_PULL_MERGE": {
        "availability": "AVAILABLE",
        "pull_request_precondition": "EXACT_PR",
        "head_precondition": "EXACT_HEAD",
        "base_precondition": "NONE",
        "protection_behavior": "RESPECTS_WITHOUT_BYPASS",
        "merge_method": "SQUASH",
        "audit_behavior": "PR_MERGED_EXACT_SHA",
        "outcome_recovery": "FRESH_STATE_RECOVERABLE",
        "source_ids": ["GITHUB_PULL_MERGE_API"],
    },
    "REST_PULL_MERGE_STRICT_RULESET": {
        "availability": "AVAILABLE",
        "pull_request_precondition": "EXACT_PR",
        "head_precondition": "EXACT_HEAD",
        "base_precondition": "STRICT_REQUIRED_STATUS",
        "protection_behavior": "RESPECTS_WITHOUT_BYPASS",
        "merge_method": "SQUASH",
        "audit_behavior": "PR_MERGED_EXACT_SHA",
        "outcome_recovery": "FRESH_STATE_RECOVERABLE",
        "source_ids": [
            "GITHUB_PULL_MERGE_API",
            "GITHUB_RULESET_DOCUMENTATION",
            "POLACORE_ENGINEERING_RULESET",
            "POLACORE_STRICT_BASE_CANARY",
        ],
    },
    "REST_PULL_MERGE_ASYNC": {
        "availability": "AVAILABLE",
        "pull_request_precondition": "EXACT_PR",
        "head_precondition": "EXACT_HEAD",
        "base_precondition": "NONE",
        "protection_behavior": "RESPECTS_WITHOUT_BYPASS",
        "merge_method": "SQUASH",
        "audit_behavior": "PR_MERGED_EXACT_SHA",
        "outcome_recovery": "EPHEMERAL_RESULT",
        "source_ids": ["GITHUB_PULL_MERGE_API"],
    },
    "REST_GIT_REF_UPDATE": {
        "availability": "AVAILABLE",
        "pull_request_precondition": "NONE",
        "head_precondition": "NONE",
        "base_precondition": "FAST_FORWARD_ONLY",
        "protection_behavior": "UNPROVEN",
        "merge_method": "UNPROVEN",
        "audit_behavior": "REF_UPDATE_ONLY",
        "outcome_recovery": "FRESH_STATE_RECOVERABLE",
        "source_ids": ["GITHUB_GIT_REF_API", "GITHUB_RULESET_DOCUMENTATION"],
    },
    "GITHUB_MERGE_QUEUE": {
        "availability": "UNAVAILABLE",
        "pull_request_precondition": "EXACT_PR",
        "head_precondition": "CURRENT_HEAD",
        "base_precondition": "LATEST_BASE",
        "protection_behavior": "RESPECTS_WITHOUT_BYPASS",
        "merge_method": "PROVIDER_SELECTED",
        "audit_behavior": "QUEUE_ENTRY",
        "outcome_recovery": "FRESH_STATE_RECOVERABLE",
        "source_ids": ["GITHUB_MERGE_QUEUE_DOCUMENTATION", "POLACORE_ENGINEERING_RULESET"],
    },
}
KNOWN_JOURNAL_CONTRACTS = {
    "NO_DURABLE_JOURNAL_ESTABLISHED": {
        "availability": "UNAVAILABLE",
        "binding": "NONE",
        "monotonicity": "NONE",
        "durability": "NONE",
        "retention": "NONE",
        "candidate_write_access": False,
        "source_ids": ["GITHUB_PULL_MERGE_API"],
    }
}
KNOWN_SOURCE_CONTRACTS = {
    "GITHUB_PULL_MERGE_API": {
        "kind": "GITHUB_PRIMARY_DOCUMENTATION",
        "url": "https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request",
        "supports": ["HEAD_SHA_ONLY", "ASYNC_RESULT_RETENTION_24H", "CONTENTS_WRITE_REQUIRED"],
    },
    "GITHUB_GIT_REF_API": {
        "kind": "GITHUB_PRIMARY_DOCUMENTATION",
        "url": "https://docs.github.com/en/rest/git/refs#update-a-reference",
        "supports": ["FAST_FORWARD_ONLY"],
    },
    "GITHUB_MERGE_QUEUE_DOCUMENTATION": {
        "kind": "GITHUB_PRIMARY_DOCUMENTATION",
        "url": "https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/incorporating-changes-from-a-pull-request/merging-a-pull-request-with-a-merge-queue",
        "supports": ["LATEST_BASE", "ORGANIZATION_REPOSITORY_ONLY"],
    },
    "GITHUB_RULESET_DOCUMENTATION": {
        "kind": "GITHUB_PRIMARY_DOCUMENTATION",
        "url": "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets",
        "supports": ["PULL_REQUEST_REQUIRED", "NO_BYPASS"],
    },
    "POLACORE_ENGINEERING_RULESET": {
        "kind": "GITHUB_AUTHENTICATED_REPOSITORY_STATE",
        "url": "https://api.github.com/repos/djibian/polacore/rulesets/21296946",
        "supports": [
            "ACTIVE_ENGINEERING_RULESET",
            "NO_BYPASS",
            "PULL_REQUEST_REQUIRED",
            "STRICT_REQUIRED_STATUS",
            "REQUIRED_BRANCH_UP_TO_DATE",
            "DETERMINISTIC_CONTRACT_REQUIRED",
        ],
    },
    "POLACORE_STRICT_BASE_CANARY": {
        "kind": "GITHUB_AUTHENTICATED_REPOSITORY_STATE",
        "url": "https://api.github.com/repos/djibian/polacore/commits/369396da9cc7fc9fd0c030a1a411b2df5bbfcf52",
        "supports": [
            "BOUNDED_CANARY_ONLY",
            "STALE_TESTED_HEAD_REJECTED_AFTER_BASE_ADVANCE",
            "FRESH_CHECK_REQUIRED_AFTER_BRANCH_UPDATE",
            "GLOBAL_REQUIRED_CHECK_LIVE",
        ],
    },
}


def boolean(value: Any, label: str) -> bool:
    if value is not True and value is not False:
        governor.reject(f"{label} must be a boolean")
    return value


def nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        governor.reject(f"{label} must be a non-negative integer")
    return value


def date(value: Any, label: str) -> str:
    text = governor.nonempty_string(value, label, 10)
    if (
        len(text) != 10
        or text[4] != "-"
        or text[7] != "-"
        or not (text[:4] + text[5:7] + text[8:]).isdigit()
    ):
        governor.reject(f"{label} must use YYYY-MM-DD")
    return text


def token_list(value: Any, label: str, *, nonempty: bool = True) -> list[str]:
    values = governor.string_list(value, label, nonempty=nonempty)
    for index, item in enumerate(values):
        governor.token(item, f"{label}[{index}]")
    return values


def source_ids(value: Any, label: str) -> list[str]:
    values = governor.string_list(value, label)
    for index, item in enumerate(values):
        governor.nonempty_string(item, f"{label}[{index}]", 80)
    return values


def validate_source(raw: Any) -> dict[str, Any]:
    source = governor.exact_keys(raw, SOURCE_KEYS, "provider source")
    source_id = governor.nonempty_string(source["id"], "provider source.id", 80)
    expected = KNOWN_SOURCE_CONTRACTS.get(source_id)
    if expected is None:
        governor.reject("provider source is not in the trusted-base source registry")
    if source["kind"] not in {
        "GITHUB_PRIMARY_DOCUMENTATION",
        "GITHUB_AUTHENTICATED_REPOSITORY_STATE",
    }:
        governor.reject("provider source is not an accepted primary-source kind")
    url = governor.nonempty_string(source["url"], "provider source.url", 500)
    if source["kind"] == "GITHUB_PRIMARY_DOCUMENTATION":
        if not url.startswith("https://docs.github.com/"):
            governor.reject("GitHub documentation source must use docs.github.com")
    elif not url.startswith("https://api.github.com/repos/djibian/polacore/"):
        governor.reject("repository-state source is outside djibian/polacore")
    date(source["retrieved_on"], "provider source.retrieved_on")
    token_list(source["supports"], "provider source.supports")
    observed = {key: source[key] for key in ("kind", "url", "supports")}
    if observed != expected:
        governor.reject("provider source semantics differ from the trusted-base registry")
    return source


def validate_ruleset(raw: Any, known_sources: set[str]) -> dict[str, Any]:
    ruleset = governor.exact_keys(raw, RULESET_KEYS, "provider ruleset")
    governor.positive_int(ruleset["id"], "provider ruleset.id")
    if ruleset["enforcement"] not in {"ACTIVE", "DISABLED"}:
        governor.reject("provider ruleset enforcement is invalid")
    for key in (
        "pull_request_required",
        "non_fast_forward_forbidden",
        "deletion_forbidden",
        "merge_queue_required",
        "current_actor_can_bypass",
        "strict_required_status",
        "required_branch_up_to_date",
    ):
        boolean(ruleset[key], f"provider ruleset.{key}")
    nonnegative_int(ruleset["bypass_actor_count"], "provider ruleset.bypass_actor_count")
    methods = token_list(ruleset["allowed_merge_methods"], "provider ruleset.allowed_merge_methods")
    token_list(ruleset["required_status_checks"], "provider ruleset.required_status_checks")
    if any(method not in {"MERGE", "REBASE", "SQUASH"} for method in methods):
        governor.reject("provider ruleset contains an unsupported merge method")
    validate_source_references(ruleset["source_ids"], known_sources, "provider ruleset")
    return ruleset


def validate_operation(raw: Any, known_sources: set[str]) -> dict[str, Any]:
    operation = governor.exact_keys(raw, OPERATION_KEYS, "provider operation")
    operation_id = governor.token(operation["id"], "provider operation.id")
    expected = KNOWN_OPERATION_CONTRACTS.get(operation_id)
    if expected is None:
        governor.reject("provider operation is not in the trusted-base operation registry")
    allowed = {
        "availability": {"AVAILABLE", "UNAVAILABLE"},
        "pull_request_precondition": {"EXACT_PR", "NONE"},
        "head_precondition": {"EXACT_HEAD", "CURRENT_HEAD", "NONE"},
        "base_precondition": {"EXACT_BASE", "STRICT_REQUIRED_STATUS", "FAST_FORWARD_ONLY", "LATEST_BASE", "NONE"},
        "protection_behavior": {"RESPECTS_WITHOUT_BYPASS", "UNPROVEN", "BYPASS"},
        "merge_method": {"SQUASH", "MERGE", "REBASE", "PROVIDER_SELECTED", "UNPROVEN"},
        "audit_behavior": {"PR_MERGED_EXACT_SHA", "QUEUE_ENTRY", "REF_UPDATE_ONLY", "UNPROVEN"},
        "outcome_recovery": {"FRESH_STATE_RECOVERABLE", "EPHEMERAL_RESULT", "UNPROVEN"},
    }
    for key, values in allowed.items():
        if operation[key] not in values:
            governor.reject(f"provider operation.{key} is invalid")
    validate_source_references(operation["source_ids"], known_sources, "provider operation")
    observed = {key: operation[key] for key in expected}
    if observed != expected:
        governor.reject("provider operation semantics differ from the trusted-base registry")
    return operation


def validate_journal(raw: Any, known_sources: set[str]) -> dict[str, Any]:
    journal = governor.exact_keys(raw, JOURNAL_KEYS, "provider journal")
    journal_id = governor.token(journal["id"], "provider journal.id")
    expected = KNOWN_JOURNAL_CONTRACTS.get(journal_id)
    if expected is None:
        governor.reject("provider journal is not in the trusted-base journal registry")
    allowed = {
        "availability": {"AVAILABLE", "UNAVAILABLE"},
        "binding": {"EXACT_BUNDLE", "NONE", "UNPROVEN"},
        "monotonicity": {"PREPARED_TO_COMPLETED_ONLY", "MUTABLE", "NONE", "UNPROVEN"},
        "durability": {"DURABLE", "EPHEMERAL", "NONE", "UNPROVEN"},
        "retention": {"INDEFINITE", "BOUNDED", "NONE", "UNPROVEN"},
    }
    for key, values in allowed.items():
        if journal[key] not in values:
            governor.reject(f"provider journal.{key} is invalid")
    boolean(journal["candidate_write_access"], "provider journal.candidate_write_access")
    validate_source_references(journal["source_ids"], known_sources, "provider journal")
    observed = {key: journal[key] for key in expected}
    if observed != expected:
        governor.reject("provider journal semantics differ from the trusted-base registry")
    return journal


def validate_source_references(raw: Any, known: set[str], label: str) -> list[str]:
    references = source_ids(raw, f"{label}.source_ids")
    missing = sorted(set(references) - known)
    if missing:
        governor.reject(f"{label} references unknown primary sources: {missing}")
    return references


def validate_evidence(raw: Any) -> dict[str, Any]:
    evidence = governor.exact_keys(raw, EVIDENCE_KEYS, "provider capability evidence")
    if evidence["schema"] != EVIDENCE_SCHEMA:
        governor.reject("unsupported provider capability evidence schema")
    if evidence["provider"] != "GITHUB_COM":
        governor.reject("provider capability evidence is not for github.com")
    if evidence["repository"] != "djibian/polacore":
        governor.reject("provider capability evidence is for another repository")
    if evidence["repository_owner_type"] not in {"USER", "ORGANIZATION"}:
        governor.reject("repository owner type is invalid")
    if evidence["target_ref"] != "engineering":
        governor.reject("provider capability target is not engineering")
    if evidence["required_merge_method"] != "SQUASH":
        governor.reject("provider capability changes the required merge method")
    date(evidence["observed_at"], "provider capability evidence.observed_at")

    sources_raw = evidence["sources"]
    if not isinstance(sources_raw, list) or not sources_raw or len(sources_raw) > 40:
        governor.reject("provider sources must be a bounded non-empty list")
    sources = [validate_source(item) for item in sources_raw]
    source_names = [source["id"] for source in sources]
    if len(source_names) != len(set(source_names)):
        governor.reject("provider sources contain duplicate ids")
    known_sources = set(source_names)

    validate_ruleset(evidence["ruleset"], known_sources)
    operations_raw = evidence["operations"]
    if not isinstance(operations_raw, list) or not operations_raw or len(operations_raw) > 20:
        governor.reject("provider operations must be a bounded non-empty list")
    operations = [validate_operation(item, known_sources) for item in operations_raw]
    operation_ids = [operation["id"] for operation in operations]
    if len(operation_ids) != len(set(operation_ids)):
        governor.reject("provider operations contain duplicate ids")
    selected = evidence["selected_operation"]
    if selected is not None:
        governor.token(selected, "provider capability evidence.selected_operation")
        if selected not in set(operation_ids):
            governor.reject("selected provider operation does not exist")
    validate_journal(evidence["journal"], known_sources)
    return evidence


def operation_reasons(operation: dict[str, Any]) -> list[str]:
    reasons = []
    for key, required in REQUIRED_OPERATION.items():
        observed = operation[key]
        if key == "base_precondition":
            if observed not in {"EXACT_BASE", "STRICT_REQUIRED_STATUS"}:
                reasons.append(
                    f"{key}={observed} requires EXACT_BASE or STRICT_REQUIRED_STATUS"
                )
        elif observed != required:
            reasons.append(f"{key}={observed} requires {required}")
    return reasons


def ruleset_reasons(ruleset: dict[str, Any]) -> list[str]:
    reasons = []
    required = {
        "enforcement": "ACTIVE",
        "pull_request_required": True,
        "non_fast_forward_forbidden": True,
        "deletion_forbidden": True,
        "current_actor_can_bypass": False,
        "bypass_actor_count": 0,
        "strict_required_status": True,
        "required_branch_up_to_date": True,
    }
    for key, expected in required.items():
        if ruleset[key] != expected:
            reasons.append(f"ruleset.{key}={ruleset[key]} requires {expected}")
    if "SQUASH" not in ruleset["allowed_merge_methods"]:
        reasons.append("ruleset does not allow SQUASH")
    if ruleset["required_status_checks"] != ["deterministic-contract"]:
        reasons.append("ruleset.required_status_checks must be exactly deterministic-contract")
    return reasons


def journal_reasons(journal: dict[str, Any]) -> list[str]:
    return [
        f"journal.{key}={journal[key]} requires {required}"
        for key, required in REQUIRED_JOURNAL.items()
        if journal[key] != required
    ]


def assess(raw: Any) -> dict[str, Any]:
    """Assess evidence without granting authority or producing a merge command."""

    evidence = validate_evidence(raw)
    rule_reasons = ruleset_reasons(evidence["ruleset"])
    assessments = []
    for operation in evidence["operations"]:
        reasons = operation_reasons(operation) + rule_reasons
        assessments.append(
            {"id": operation["id"], "status": "ELIGIBLE" if not reasons else "UNPROVEN", "reasons": reasons}
        )
    journal_missing = journal_reasons(evidence["journal"])
    selected = evidence["selected_operation"]
    selected_assessment = next((item for item in assessments if item["id"] == selected), None)
    eligible = selected_assessment is not None and selected_assessment["status"] == "ELIGIBLE"
    eligible = eligible and not journal_missing
    reasons = []
    if selected is None:
        reasons.append("no provider operation has been selected by trusted policy")
    elif selected_assessment is not None:
        reasons.extend(selected_assessment["reasons"])
    reasons.extend(journal_missing)
    return {
        "schema": ASSESSMENT_SCHEMA,
        "decision": "ELIGIBLE" if eligible else "UNPROVEN",
        "repository": evidence["repository"],
        "target_ref": evidence["target_ref"],
        "required_merge_method": evidence["required_merge_method"],
        "evidence_sha256": governor.digest(evidence),
        "selected_operation": selected,
        "operation_assessments": assessments,
        "journal_status": "ELIGIBLE" if not journal_missing else "UNPROVEN",
        "reasons": reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=pathlib.Path)
    args = parser.parse_args()
    try:
        result = assess(governor.load_json(args.evidence))
    except governor.Rejected as exc:
        result = {"decision": "UNPROVEN", "reason": str(exc)}
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["decision"] == "ELIGIBLE" else 3


if __name__ == "__main__":
    sys.exit(main())
