#!/usr/bin/env python3
"""Pure compare-and-swap protocol for a future privileged merge adapter.

This module has no GitHub client, token, network, subprocess, or concrete
storage implementation.  It verifies a trusted-base decision bundle and drives
only an injected adapter whose live authority remains a separate obligation.
"""

from __future__ import annotations

from typing import Any, Protocol

import merge_decision_bundle as bundler
import merge_governor as governor


LIVE_STATE_SCHEMA = "polacore.merge-live-state/v1"
JOURNAL_SCHEMA = "polacore.merge-controller-journal/v1"
CAS_REQUEST_SCHEMA = "polacore.merge-cas-request/v1"
CAS_RESULT_SCHEMA = "polacore.merge-cas-result/v1"
CONTROLLER_RESULT_SCHEMA = "polacore.merge-controller-result/v1"

LIVE_STATE_KEYS = {
    "schema",
    "repository",
    "pull_request",
    "base_ref",
    "current_target_sha",
    "head_repo",
    "head_ref",
    "head_sha",
    "state",
    "draft",
    "mergeable",
    "merged",
    "merge_sha",
    "protection_bypass_requested",
}
JOURNAL_KEYS = {
    "schema",
    "state",
    "repository",
    "pull_request",
    "target_ref",
    "base_sha",
    "head_sha",
    "merge_method",
    "bundle_binding_sha256",
    "certificate_sha256",
    "observation_sha256",
    "policy_sha256",
    "decision_sha256",
    "merge_sha",
    "completion_kind",
}
CAS_REQUEST_KEYS = {
    "schema",
    "repository",
    "pull_request",
    "target_ref",
    "expected_base_sha",
    "expected_head_sha",
    "merge_method",
    "bundle_binding_sha256",
    "certificate_sha256",
    "policy_sha256",
    "decision_sha256",
}
CAS_RESULT_KEYS = {
    "schema",
    "status",
    "repository",
    "pull_request",
    "expected_base_sha",
    "expected_head_sha",
    "merge_sha",
}


class AdapterError(RuntimeError):
    """The injected adapter could not establish whether an operation completed."""


class ControllerAdapter(Protocol):
    """Minimal interface; journal writes are durable, keyed, and monotonic."""

    def read_state(self, repository: str, pull_request: int) -> dict[str, Any]: ...

    def read_journal(self, bundle_binding_sha256: str) -> dict[str, Any] | None: ...

    def prepare(self, entry: dict[str, Any]) -> None: ...

    def merge_squash_compare_and_swap(self, request: dict[str, Any]) -> dict[str, Any]: ...

    def complete(self, entry: dict[str, Any]) -> None: ...


def sha256_digest(value: Any, label: str) -> str:
    text = governor.nonempty_string(value, label, 71)
    invalid_hex = any(character not in "0123456789abcdef" for character in text[7:])
    if len(text) != 71 or not text.startswith("sha256:") or invalid_hex:
        governor.reject(f"{label} must be a lowercase SHA-256 digest")
    return text


def validate_live_state(raw: Any) -> dict[str, Any]:
    state = governor.exact_keys(raw, LIVE_STATE_KEYS, "live state")
    if state["schema"] != LIVE_STATE_SCHEMA:
        governor.reject("unsupported live state schema")
    governor.nonempty_string(state["repository"], "live state.repository", 200)
    governor.positive_int(state["pull_request"], "live state.pull_request")
    governor.nonempty_string(state["base_ref"], "live state.base_ref", 100)
    governor.sha(state["current_target_sha"], "live state.current_target_sha")
    governor.nonempty_string(state["head_repo"], "live state.head_repo", 200)
    governor.nonempty_string(state["head_ref"], "live state.head_ref", 250)
    governor.sha(state["head_sha"], "live state.head_sha")
    if state["draft"] is not True and state["draft"] is not False:
        governor.reject("live state draft flag has invalid type")
    mergeable = state["mergeable"]
    if mergeable is not True and mergeable is not False and mergeable is not None:
        governor.reject("live state mergeability has invalid type")
    if state["merged"] is not True and state["merged"] is not False:
        governor.reject("live state merged flag has invalid type")
    if state["protection_bypass_requested"] is not False:
        governor.reject("live state requests a protection bypass")

    if state["state"] == "OPEN":
        if state["merged"] is not False or state["merge_sha"] is not None:
            governor.reject("open live state has contradictory merge fields")
    elif state["state"] == "MERGED":
        if state["merged"] is not True:
            governor.reject("merged live state is not marked merged")
        governor.sha(state["merge_sha"], "live state.merge_sha")
    else:
        governor.reject("unsupported live pull-request state")
    return state


def expected_journal(
    bundle: dict[str, Any],
    *,
    merge_sha: str | None = None,
    completion_kind: str | None = None,
) -> dict[str, Any]:
    intent = bundle["intent"]
    completed = merge_sha is not None
    if completed:
        governor.sha(merge_sha, "journal.merge_sha")
        if completion_kind not in {"CAS_CONFIRMED", "OBSERVED_AFTER_PREPARE"}:
            governor.reject("completed journal has invalid completion kind")
    elif completion_kind is not None:
        governor.reject("prepared journal may not have a completion kind")
    return {
        "schema": JOURNAL_SCHEMA,
        "state": "COMPLETED" if completed else "PREPARED",
        "repository": intent["repository"],
        "pull_request": intent["pull_request"],
        "target_ref": intent["target_ref"],
        "base_sha": intent["base_sha"],
        "head_sha": intent["head_sha"],
        "merge_method": intent["merge_method"],
        "bundle_binding_sha256": bundle["binding_sha256"],
        "certificate_sha256": bundle["certificate_sha256"],
        "observation_sha256": bundle["observation_sha256"],
        "policy_sha256": intent["policy_sha256"],
        "decision_sha256": bundle["decision_sha256"],
        "merge_sha": merge_sha,
        "completion_kind": completion_kind,
    }


def validate_journal(raw: Any, bundle: dict[str, Any]) -> dict[str, Any]:
    entry = governor.exact_keys(raw, JOURNAL_KEYS, "controller journal")
    if entry["schema"] != JOURNAL_SCHEMA:
        governor.reject("unsupported controller journal schema")
    if entry["state"] == "PREPARED":
        expected = expected_journal(bundle)
    elif entry["state"] == "COMPLETED":
        expected = expected_journal(
            bundle,
            merge_sha=governor.sha(entry["merge_sha"], "controller journal.merge_sha"),
            completion_kind=entry["completion_kind"],
        )
    else:
        governor.reject("unsupported controller journal state")
    if entry != expected:
        governor.reject("controller journal does not match the exact verified bundle")
    return entry


def cas_request(bundle: dict[str, Any]) -> dict[str, Any]:
    intent = bundle["intent"]
    if intent["disposition"] != "PROPOSE_MERGE" or intent["merge_method"] != "squash":
        governor.reject("bundle does not contain a squash merge proposal")
    return {
        "schema": CAS_REQUEST_SCHEMA,
        "repository": intent["repository"],
        "pull_request": intent["pull_request"],
        "target_ref": intent["target_ref"],
        "expected_base_sha": intent["base_sha"],
        "expected_head_sha": intent["head_sha"],
        "merge_method": "squash",
        "bundle_binding_sha256": bundle["binding_sha256"],
        "certificate_sha256": bundle["certificate_sha256"],
        "policy_sha256": intent["policy_sha256"],
        "decision_sha256": bundle["decision_sha256"],
    }


def validate_cas_result(raw: Any, request: dict[str, Any]) -> dict[str, Any]:
    result = governor.exact_keys(raw, CAS_RESULT_KEYS, "CAS result")
    if result["schema"] != CAS_RESULT_SCHEMA:
        governor.reject("unsupported CAS result schema")
    for result_key, request_key in (
        ("repository", "repository"),
        ("pull_request", "pull_request"),
        ("expected_base_sha", "expected_base_sha"),
        ("expected_head_sha", "expected_head_sha"),
    ):
        if result[result_key] != request[request_key]:
            governor.reject("CAS result is bound to another request")
    if result["status"] == "APPLIED":
        governor.sha(result["merge_sha"], "CAS result.merge_sha")
    elif result["status"] in {"STALE", "UNCERTAIN"}:
        if result["merge_sha"] is not None:
            governor.reject("non-applied CAS result may not claim a merge SHA")
    else:
        governor.reject("unsupported CAS result status")
    return result


def controller_result(
    bundle: dict[str, Any],
    status: str,
    *,
    merge_sha: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    if merge_sha is not None:
        governor.sha(merge_sha, "controller result.merge_sha")
    return {
        "schema": CONTROLLER_RESULT_SCHEMA,
        "status": status,
        "repository": bundle["intent"]["repository"],
        "pull_request": bundle["intent"]["pull_request"],
        "base_sha": bundle["intent"]["base_sha"],
        "head_sha": bundle["intent"]["head_sha"],
        "bundle_binding_sha256": bundle["binding_sha256"],
        "merge_sha": merge_sha,
        "reason": reason,
    }


def common_state_checks(state: dict[str, Any], bundle: dict[str, Any]) -> None:
    intent = bundle["intent"]
    certificate = bundle["certificate"]
    if state["repository"] != intent["repository"] or state["pull_request"] != intent["pull_request"]:
        governor.reject("live state identifies another repository or pull request")
    if state["base_ref"] != intent["target_ref"] or intent["target_ref"] != "engineering":
        governor.reject("live state target is not engineering")
    if state["head_repo"] != certificate["head_repo"] or state["head_ref"] != certificate["head_ref"]:
        governor.reject("live state head repository or branch changed")
    if state["draft"] is not False:
        governor.reject("draft pull request is not actionable")


def exact_open_state(state: dict[str, Any], bundle: dict[str, Any]) -> bool:
    intent = bundle["intent"]
    return (
        state["state"] == "OPEN"
        and state["current_target_sha"] == intent["base_sha"]
        and state["head_sha"] == intent["head_sha"]
        and state["mergeable"] is True
    )


def exact_merged_state(
    state: dict[str, Any],
    bundle: dict[str, Any],
    expected_merge_sha: str | None = None,
) -> bool:
    if state["state"] != "MERGED" or state["head_sha"] != bundle["intent"]["head_sha"]:
        return False
    return expected_merge_sha is None or state["merge_sha"] == expected_merge_sha


def finish_journal(
    adapter: ControllerAdapter,
    bundle: dict[str, Any],
    merge_sha: str,
    completion_kind: str,
    success_status: str,
) -> dict[str, Any]:
    completed = expected_journal(bundle, merge_sha=merge_sha, completion_kind=completion_kind)
    try:
        adapter.complete(dict(completed))
    except AdapterError:
        pass
    persisted = adapter.read_journal(bundle["binding_sha256"])
    if persisted is None:
        return controller_result(
            bundle, "MERGED_RECORD_UNCONFIRMED", merge_sha=merge_sha,
            reason="completed merge record was not durably confirmed",
        )
    verified = validate_journal(persisted, bundle)
    if verified != completed:
        return controller_result(
            bundle, "MERGED_RECORD_UNCONFIRMED", merge_sha=merge_sha,
            reason="journal remains prepared after an observed merge",
        )
    return controller_result(bundle, success_status, merge_sha=merge_sha)


def execute(
    policy: dict[str, Any],
    bundle: dict[str, Any],
    adapter: ControllerAdapter,
) -> dict[str, Any]:
    """Execute at most one atomic merge request for one verified bundle."""

    bundler.verify_bundle(policy, bundle)
    binding = sha256_digest(bundle["binding_sha256"], "bundle.binding_sha256")
    intent = bundle["intent"]
    journal_raw = adapter.read_journal(binding)
    journal = validate_journal(journal_raw, bundle) if journal_raw is not None else None
    live = validate_live_state(adapter.read_state(intent["repository"], intent["pull_request"]))
    common_state_checks(live, bundle)

    if intent["disposition"] == "NO_ACTION_ALREADY_MERGED":
        recorded = governor.sha(intent["recorded_merge_sha"], "intent.recorded_merge_sha")
        if not exact_merged_state(live, bundle, recorded):
            governor.reject("live state does not corroborate the already-merged bundle")
        return controller_result(bundle, "NO_ACTION_ALREADY_MERGED", merge_sha=recorded)
    if intent["disposition"] != "PROPOSE_MERGE" or intent["fresh_compare_and_swap_required"] is not True:
        governor.reject("unsupported or non-CAS merge intent")

    if journal is not None and journal["state"] == "COMPLETED":
        if not exact_merged_state(live, bundle, journal["merge_sha"]):
            governor.reject("completed journal is contradicted by live GitHub state")
        return controller_result(bundle, "ALREADY_RECORDED", merge_sha=journal["merge_sha"])

    if live["state"] == "MERGED":
        if journal is None or journal["state"] != "PREPARED" or not exact_merged_state(live, bundle):
            governor.reject("merged state has no matching durable prepared intent")
        return finish_journal(
            adapter, bundle, live["merge_sha"], "OBSERVED_AFTER_PREPARE", "RECOVERED_RECORDED"
        )

    if not exact_open_state(live, bundle):
        return controller_result(
            bundle, "STOP_STALE", reason="fresh base, head, or mergeability no longer matches the bundle"
        )

    prepared = expected_journal(bundle)
    if journal is None:
        try:
            adapter.prepare(dict(prepared))
        except AdapterError:
            pass
        persisted = adapter.read_journal(binding)
        if persisted is None:
            return controller_result(
                bundle, "RETRY_REQUIRED", reason="prepared intent was not durably confirmed"
            )
        journal = validate_journal(persisted, bundle)
    if journal != prepared:
        governor.reject("merge may proceed only from the exact prepared journal state")

    request = cas_request(bundle)
    try:
        cas_raw = adapter.merge_squash_compare_and_swap(dict(request))
        cas = validate_cas_result(cas_raw, request)
    except AdapterError:
        cas = {
            "schema": CAS_RESULT_SCHEMA,
            "status": "UNCERTAIN",
            "repository": request["repository"],
            "pull_request": request["pull_request"],
            "expected_base_sha": request["expected_base_sha"],
            "expected_head_sha": request["expected_head_sha"],
            "merge_sha": None,
        }

    if cas["status"] == "STALE":
        return controller_result(bundle, "STOP_STALE", reason="atomic compare-and-swap rejected stale state")

    after = validate_live_state(adapter.read_state(intent["repository"], intent["pull_request"]))
    common_state_checks(after, bundle)
    if exact_merged_state(after, bundle):
        if cas["status"] == "APPLIED" and cas["merge_sha"] != after["merge_sha"]:
            governor.reject("CAS result and fresh merged state disagree on merge SHA")
        completion_kind = "CAS_CONFIRMED" if cas["status"] == "APPLIED" else "OBSERVED_AFTER_PREPARE"
        success_status = "MERGED_RECORDED" if cas["status"] == "APPLIED" else "RECOVERED_RECORDED"
        return finish_journal(adapter, bundle, after["merge_sha"], completion_kind, success_status)
    if exact_open_state(after, bundle):
        status = "MERGE_OUTCOME_UNCONFIRMED" if cas["status"] == "APPLIED" else "RETRY_REQUIRED"
        return controller_result(
            bundle, status, reason="no merged state was observed after the single CAS attempt"
        )
    return controller_result(
        bundle, "STOP_STALE", reason="state changed during the compare-and-swap attempt"
    )
