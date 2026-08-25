#!/usr/bin/env python3
"""Build and verify a non-authoritative Merge Governor decision bundle.

The module composes the offline certificate builder, authenticated-snapshot
normalizer and pure Governor. It emits data and a proposed disposition only; it
never contacts GitHub, executes candidate code, publishes, or merges.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

import merge_certificate_build as certificate_builder
import merge_governor as governor
import merge_observation_collect as observation_collector


BUNDLE_SCHEMA = "polacore.merge-decision-bundle/v1"
INTENT_SCHEMA = "polacore.merge-intent/v1"
BINDING_SCHEMA = "polacore.merge-bundle-binding/v1"
BUNDLE_KEYS = {
    "schema",
    "certificate",
    "certificate_sha256",
    "observation",
    "observation_sha256",
    "decision",
    "decision_sha256",
    "intent",
    "intent_sha256",
    "binding_sha256",
}
INTENT_KEYS = {
    "schema",
    "disposition",
    "repository",
    "pull_request",
    "target_ref",
    "base_sha",
    "head_sha",
    "merge_method",
    "certificate_sha256",
    "observation_sha256",
    "policy_sha256",
    "decision_sha256",
    "recorded_merge_sha",
    "fresh_compare_and_swap_required",
}


def binding_payload(bundle: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": BINDING_SCHEMA,
        "certificate_sha256": bundle["certificate_sha256"],
        "observation_sha256": bundle["observation_sha256"],
        "decision_sha256": bundle["decision_sha256"],
        "intent_sha256": bundle["intent_sha256"],
    }


def build_intent(
    policy: dict[str, Any],
    certificate: dict[str, Any],
    observation: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    decision_sha256 = governor.digest(decision)
    state = decision.get("decision")
    if state == "ELIGIBLE":
        disposition = "PROPOSE_MERGE"
        merge_method: str | None = "squash"
        merge_sha: str | None = None
        fresh_compare_and_swap_required = True
    elif state == "ALREADY_MERGED":
        disposition = "NO_ACTION_ALREADY_MERGED"
        merge_method = None
        merge_sha = governor.sha(decision.get("merge_sha"), "decision.merge_sha")
        fresh_compare_and_swap_required = False
    else:
        governor.reject("only an eligible or already-merged decision can produce an intent")

    return {
        "schema": INTENT_SCHEMA,
        "disposition": disposition,
        "repository": certificate["repository"],
        "pull_request": certificate["pull_request"],
        "target_ref": policy["integration_branch"],
        "base_sha": certificate["base_sha"],
        "head_sha": certificate["head_sha"],
        "merge_method": merge_method,
        "certificate_sha256": governor.digest(certificate),
        "observation_sha256": governor.digest(observation),
        "policy_sha256": governor.policy_digest(policy),
        "decision_sha256": decision_sha256,
        "recorded_merge_sha": merge_sha,
        "fresh_compare_and_swap_required": fresh_compare_and_swap_required,
    }


def verify_bundle(policy: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    """Recompute every bundle component and reject any tampering."""

    governor.validate_policy(policy)
    governor.exact_keys(bundle, BUNDLE_KEYS, "decision bundle")
    if bundle["schema"] != BUNDLE_SCHEMA:
        governor.reject("unsupported decision bundle schema")

    certificate = governor.exact_keys(bundle["certificate"], governor.CERTIFICATE_KEYS, "bundle.certificate")
    observation = governor.exact_keys(bundle["observation"], governor.OBSERVATION_KEYS, "bundle.observation")
    if bundle["certificate_sha256"] != governor.digest(certificate):
        governor.reject("bundle certificate digest mismatch")
    if bundle["observation_sha256"] != governor.digest(observation):
        governor.reject("bundle observation digest mismatch")

    decision = governor.evaluate(policy, certificate, observation)
    if bundle["decision"] != decision or bundle["decision_sha256"] != governor.digest(decision):
        governor.reject("bundle decision is stale, substituted, or mismatched")

    intent = governor.exact_keys(bundle["intent"], INTENT_KEYS, "bundle.intent")
    expected_intent = build_intent(policy, certificate, observation, decision)
    if intent != expected_intent or bundle["intent_sha256"] != governor.digest(expected_intent):
        governor.reject("bundle intent is stale, substituted, or mismatched")
    if bundle["binding_sha256"] != governor.digest(binding_payload(bundle)):
        governor.reject("bundle binding digest mismatch")
    return bundle


def build_bundle(
    policy: dict[str, Any],
    manifest: dict[str, Any],
    claims: dict[str, Any],
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    certificate = certificate_builder.build_certificate(policy, manifest, claims)
    observation = observation_collector.collect(policy, manifest, snapshot)
    decision = governor.evaluate(policy, certificate, observation)
    intent = build_intent(policy, certificate, observation, decision)
    bundle = {
        "schema": BUNDLE_SCHEMA,
        "certificate": certificate,
        "certificate_sha256": governor.digest(certificate),
        "observation": observation,
        "observation_sha256": governor.digest(observation),
        "decision": decision,
        "decision_sha256": governor.digest(decision),
        "intent": intent,
        "intent_sha256": governor.digest(intent),
        "binding_sha256": "",
    }
    bundle["binding_sha256"] = governor.digest(binding_payload(bundle))
    return verify_bundle(policy, bundle)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", required=True, type=pathlib.Path)
    parser.add_argument("--task", required=True, type=pathlib.Path)
    parser.add_argument("--claims", required=True, type=pathlib.Path)
    parser.add_argument("--snapshot", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()

    try:
        result = build_bundle(
            governor.load_json(args.policy),
            governor.load_json(args.task),
            governor.load_json(args.claims),
            governor.load_json(args.snapshot),
        )
        status = 0
    except (governor.Rejected, ValueError) as exc:
        result = {"decision": "UNPROVEN", "reason": str(exc)}
        status = 1

    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    args.output.write_text(payload, encoding="utf-8")
    sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    raise SystemExit(status)


if __name__ == "__main__":
    main()
