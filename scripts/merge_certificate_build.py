#!/usr/bin/env python3
"""Build a canonical Merge Governor certificate from bounded evidence claims.

The builder is pure, offline, and non-authoritative. The trusted task manifest
supplies task authority and assurance; claims can only propose candidate-bound
facts. A separately collected GitHub observation must corroborate every emitted
certificate field before the Governor may return ELIGIBLE.
"""

from __future__ import annotations

import argparse
import copy
import json
import pathlib
import sys
from typing import Any

import merge_governor as governor
from merge_observation_collect import validate_manifest


CLAIMS_SCHEMA = "polacore.merge-certificate-claims/v1"
CLAIMS_KEYS = {
    "schema",
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


def _bind_checks(
    claims: Any,
    rules: list[dict[str, Any]],
    head_sha: str,
    base_sha: str,
) -> list[dict[str, Any]]:
    entries = governor.validate_checks(claims, head_sha, base_sha, "certificate claims.checks")
    by_name = {entry["name"]: entry for entry in entries}
    if set(by_name) != {rule["name"] for rule in rules}:
        governor.reject("certificate claims do not exactly match manifest check names")
    ordered: list[dict[str, Any]] = []
    for rule in rules:
        entry = by_name[rule["name"]]
        for key in ("kind", "workflow", "workflow_path"):
            if entry[key] != rule[key]:
                governor.reject(f"check {rule['name']} does not match manifest {key}")
        ordered.append(copy.deepcopy(entry))
    return ordered


def _bind_verdicts(
    claims: Any,
    rules: list[dict[str, Any]],
    head_sha: str,
    base_sha: str,
) -> list[dict[str, Any]]:
    entries = governor.validate_verdicts(claims, head_sha, base_sha, "certificate claims.verdicts")
    by_role = {entry["role"]: entry for entry in entries}
    if set(by_role) != {rule["role"] for rule in rules}:
        governor.reject("certificate claims do not exactly match manifest verdict roles")
    ordered: list[dict[str, Any]] = []
    for rule in rules:
        entry = by_role[rule["role"]]
        for key in ("workflow", "workflow_path"):
            if entry[key] != rule[key]:
                governor.reject(f"verdict {rule['role']} does not match manifest {key}")
        ordered.append(copy.deepcopy(entry))
    return ordered


def build_certificate(
    policy: dict[str, Any],
    manifest: dict[str, Any],
    claims: dict[str, Any],
) -> dict[str, Any]:
    """Return a canonical certificate or reject any unbound authority."""

    governor.validate_policy(policy)
    task, check_rules, verdict_rules = validate_manifest(policy, manifest)
    governor.exact_keys(claims, CLAIMS_KEYS, "certificate claims")
    if claims["schema"] != CLAIMS_SCHEMA:
        governor.reject("unsupported certificate claims schema")

    repository = governor.nonempty_string(claims["repository"], "certificate claims.repository", 200)
    if repository != policy["repository"]:
        governor.reject("certificate claims repository is outside trusted policy")
    pull_request = governor.positive_int(claims["pull_request"], "certificate claims.pull_request")
    if pull_request != manifest["pull_request"]:
        governor.reject("certificate claims pull request does not match trusted manifest")
    if claims["base_ref"] != policy["integration_branch"]:
        governor.reject("certificate claims base is not engineering")

    base_sha = governor.sha(claims["base_sha"], "certificate claims.base_sha")
    head_sha = governor.sha(claims["head_sha"], "certificate claims.head_sha")
    if base_sha == head_sha:
        governor.reject("certificate claims head must differ from base")
    if claims["head_repo"] != repository:
        governor.reject("fork certificate claims are forbidden")
    head_ref = governor.nonempty_string(claims["head_ref"], "certificate claims.head_ref", 250)
    if not any(head_ref.startswith(prefix) for prefix in policy["authorized_head_prefixes"]):
        governor.reject("certificate claims head is outside the authorized agent namespace")

    assurance = governor.token(manifest["assurance"], "task manifest.assurance")
    if assurance in policy["non_autonomous_profiles"]:
        governor.reject("objective amendments cannot produce autonomous certificates")

    changes = copy.deepcopy(claims["changes"])
    paths = governor.validate_changes(changes, "certificate claims.changes")
    for path in paths:
        if governor.is_forbidden(policy, path):
            governor.reject(f"certificate claims change forbidden authority path: {path}")
        if not any(governor.pattern_matches(pattern, path) for pattern in task["authorized_paths"]):
            governor.reject(f"certificate claims change outside task authority: {path}")
    floor = governor.required_assurance(policy, paths)
    if policy["assurance_order"].index(assurance) < policy["assurance_order"].index(floor):
        governor.reject(f"task assurance {assurance} is below deterministic path floor {floor}")

    checks = _bind_checks(claims["checks"], check_rules, head_sha, base_sha)
    verdicts = _bind_verdicts(claims["verdicts"], verdict_rules, head_sha, base_sha)
    if {entry["job_id"] for entry in checks} & {entry["job_id"] for entry in verdicts}:
        governor.reject("check and verdict claims reuse one GitHub job")

    return {
        "schema": governor.CERTIFICATE_SCHEMA,
        "repository": repository,
        "pull_request": pull_request,
        "base_ref": claims["base_ref"],
        "base_sha": base_sha,
        "head_repo": claims["head_repo"],
        "head_ref": head_ref,
        "head_sha": head_sha,
        "assurance": assurance,
        "task": copy.deepcopy(task),
        "changes": changes,
        "checks": checks,
        "verdicts": verdicts,
        "policy_version": policy["version"],
        "policy_sha256": governor.policy_digest(policy),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", required=True, type=pathlib.Path)
    parser.add_argument("--task", required=True, type=pathlib.Path)
    parser.add_argument("--claims", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()

    try:
        result = build_certificate(
            governor.load_json(args.policy),
            governor.load_json(args.task),
            governor.load_json(args.claims),
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
