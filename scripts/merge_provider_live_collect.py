#!/usr/bin/env python3
"""Collect trusted GitHub provider evidence through authenticated GET requests.

This client is deliberately narrow: two fixed github.com repository endpoints,
GET only, bounded JSON responses, no redirects outside the allowlist, no
candidate checkout/execution, and no write/merge operation. Missing fields,
including hidden bypass actors, fail closed.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
from typing import Any, Callable

import merge_governor as governor
import merge_provider_capability as capability


LIVE_SCHEMA = "polacore.merge-provider-live-observation/v1"
API_ROOT = "https://api.github.com"
API_VERSION = "2022-11-28"
REPOSITORY = "djibian/polacore"
RULESET_ID = 21296946
REPOSITORY_PATH = "/repos/djibian/polacore"
RULESET_PATH = f"{REPOSITORY_PATH}/rulesets/{RULESET_ID}"
ALLOWED_PATHS = {REPOSITORY_PATH, RULESET_PATH}
MAX_RESPONSE_BYTES = 1_000_000

Fetch = Callable[[str], tuple[dict[str, Any], dict[str, str]]]


def mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        governor.reject(f"{label} must be an object")
    return value


def sequence(value: Any, label: str, limit: int = 100) -> list[Any]:
    if not isinstance(value, list) or len(value) > limit:
        governor.reject(f"{label} must be a list of at most {limit} items")
    return value


def field(value: Any, name: str, label: str) -> Any:
    obj = mapping(value, label)
    if name not in obj:
        governor.reject(f"{label}.{name} is missing")
    return obj[name]


def boolean(value: Any, label: str) -> bool:
    if value is not True and value is not False:
        governor.reject(f"{label} must be a boolean")
    return value


def exact_rule(rules: list[Any], kind: str) -> dict[str, Any] | None:
    matches = [mapping(item, f"ruleset rule {kind}") for item in rules if isinstance(item, dict) and item.get("type") == kind]
    if len(matches) > 1:
        governor.reject(f"ruleset contains duplicate {kind} rules")
    return matches[0] if matches else None


def parse_ruleset(repo: dict[str, Any], ruleset: dict[str, Any]) -> dict[str, Any]:
    if field(repo, "full_name", "repository") != REPOSITORY:
        governor.reject("repository identity differs from trusted policy")
    owner = mapping(field(repo, "owner", "repository"), "repository.owner")
    owner_type = field(owner, "type", "repository.owner")
    if owner_type not in {"User", "Organization"}:
        governor.reject("repository owner type is unsupported")
    if boolean(field(repo, "allow_squash_merge", "repository"), "repository.allow_squash_merge") is not True:
        governor.reject("repository does not allow the required squash merge method")

    if field(ruleset, "id", "ruleset") != RULESET_ID:
        governor.reject("ruleset identity differs from trusted policy")
    if field(ruleset, "name", "ruleset") != "Protect engineering":
        governor.reject("ruleset name differs from governed engineering ruleset")
    if field(ruleset, "target", "ruleset") != "branch":
        governor.reject("ruleset does not target branches")
    if field(ruleset, "source", "ruleset") != REPOSITORY:
        governor.reject("ruleset source differs from trusted repository")
    if field(ruleset, "source_type", "ruleset") != "Repository":
        governor.reject("ruleset is not repository-owned")

    conditions = mapping(field(ruleset, "conditions", "ruleset"), "ruleset.conditions")
    ref_name = mapping(field(conditions, "ref_name", "ruleset.conditions"), "ruleset.conditions.ref_name")
    includes = sequence(field(ref_name, "include", "ruleset.conditions.ref_name"), "ruleset include")
    excludes = sequence(field(ref_name, "exclude", "ruleset.conditions.ref_name"), "ruleset exclude")
    if "refs/heads/engineering" not in includes or "refs/heads/engineering" in excludes:
        governor.reject("ruleset does not unambiguously include engineering")

    # GitHub documents that bypass_actors is omitted unless the caller has write
    # access to the ruleset. Omission is therefore unknown, never an empty list.
    if "bypass_actors" not in ruleset:
        governor.reject("ruleset.bypass_actors is hidden; no-bypass is UNPROVEN")
    bypass = sequence(ruleset["bypass_actors"], "ruleset.bypass_actors")

    rules = sequence(field(ruleset, "rules", "ruleset"), "ruleset.rules")
    pull_request = exact_rule(rules, "pull_request")
    required_status = exact_rule(rules, "required_status_checks")
    deletion = exact_rule(rules, "deletion")
    non_fast_forward = exact_rule(rules, "non_fast_forward")
    merge_queue = exact_rule(rules, "merge_queue")

    methods: list[str] = []
    if pull_request is not None:
        params = mapping(field(pull_request, "parameters", "pull request rule"), "pull request parameters")
        raw_methods = sequence(field(params, "allowed_merge_methods", "pull request parameters"), "allowed merge methods")
        for index, method in enumerate(raw_methods):
            value = governor.nonempty_string(method, f"allowed merge methods[{index}]", 20).upper()
            if value not in {"MERGE", "REBASE", "SQUASH"}:
                governor.reject("ruleset contains an unknown merge method")
            methods.append(value)

    strict = False
    checks: list[str] = []
    if required_status is not None:
        params = mapping(field(required_status, "parameters", "required status rule"), "required status parameters")
        strict = boolean(
            field(params, "strict_required_status_checks_policy", "required status parameters"),
            "required status parameters.strict_required_status_checks_policy",
        )
        raw_checks = sequence(
            field(params, "required_status_checks", "required status parameters"),
            "required status checks",
        )
        for index, raw in enumerate(raw_checks):
            check = mapping(raw, f"required status checks[{index}]")
            context = governor.nonempty_string(
                field(check, "context", f"required status checks[{index}]"),
                f"required status checks[{index}].context",
                100,
            )
            checks.append(context)
    if len(checks) != len(set(checks)):
        governor.reject("ruleset contains duplicate required status checks")

    return {
        "repository_owner_type": owner_type.upper(),
        "ruleset": {
            "id": RULESET_ID,
            "enforcement": str(field(ruleset, "enforcement", "ruleset")).upper(),
            "pull_request_required": pull_request is not None,
            "non_fast_forward_forbidden": non_fast_forward is not None,
            "deletion_forbidden": deletion is not None,
            "merge_queue_required": merge_queue is not None,
            "bypass_actor_count": len(bypass),
            # Conservative: any configured bypass actor invalidates this
            # no-bypass composite, regardless of the current token identity.
            "current_actor_can_bypass": bool(bypass),
            "allowed_merge_methods": methods,
            "required_status_checks": checks,
            "strict_required_status": strict,
            "required_branch_up_to_date": strict and bool(checks),
            "source_ids": [
                "POLACORE_ENGINEERING_RULESET",
                "POLACORE_STRICT_BASE_CANARY",
            ],
        },
    }


def build_evidence(repo: dict[str, Any], ruleset: dict[str, Any], observed_on: str) -> dict[str, Any]:
    state = parse_ruleset(repo, ruleset)
    operations = [
        {"id": operation_id, **copy.deepcopy(contract)}
        for operation_id, contract in capability.KNOWN_OPERATION_CONTRACTS.items()
    ]
    sources = [
        {
            "id": source_id,
            **copy.deepcopy(contract),
            "retrieved_on": observed_on,
        }
        for source_id, contract in capability.KNOWN_SOURCE_CONTRACTS.items()
    ]
    journal_id = "NO_DURABLE_JOURNAL_ESTABLISHED"
    evidence = {
        "schema": capability.EVIDENCE_SCHEMA,
        "provider": "GITHUB_COM",
        "repository": REPOSITORY,
        "repository_owner_type": state["repository_owner_type"],
        "target_ref": "engineering",
        "required_merge_method": "SQUASH",
        "observed_at": observed_on,
        "ruleset": state["ruleset"],
        "operations": operations,
        "journal": {
            "id": journal_id,
            **copy.deepcopy(capability.KNOWN_JOURNAL_CONTRACTS[journal_id]),
        },
        "selected_operation": "REST_PULL_MERGE_STRICT_RULESET",
        "sources": sources,
    }
    capability.validate_evidence(evidence)
    return evidence


def collect(fetch: Fetch, now: dt.datetime) -> dict[str, Any]:
    if now.tzinfo is None or now.utcoffset() is None:
        governor.reject("collector time must be timezone-aware")
    repo, repo_meta = fetch(REPOSITORY_PATH)
    ruleset, ruleset_meta = fetch(RULESET_PATH)
    evidence = build_evidence(repo, ruleset, now.date().isoformat())
    assessment = capability.assess(evidence)
    return {
        "schema": LIVE_SCHEMA,
        "repository": REPOSITORY,
        "observed_at": now.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "requests": [
            {"path": REPOSITORY_PATH, "request_id": governor.nonempty_string(repo_meta.get("request_id"), "repository request id", 200)},
            {"path": RULESET_PATH, "request_id": governor.nonempty_string(ruleset_meta.get("request_id"), "ruleset request id", 200)},
        ],
        "evidence": evidence,
        "assessment": assessment,
    }


class GitHubGetClient:
    def __init__(self, token: str, opener: Any = None) -> None:
        self._token = governor.nonempty_string(token, "GitHub token", 10_000)
        self._opener = opener or urllib.request.build_opener()

    def fetch(self, path: str) -> tuple[dict[str, Any], dict[str, str]]:
        if path not in ALLOWED_PATHS:
            governor.reject("GitHub endpoint is outside the read-only allowlist")
        url = API_ROOT + path
        request = urllib.request.Request(
            url,
            method="GET",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self._token}",
                "User-Agent": "polacore-merge-provider-readonly/1",
                "X-GitHub-Api-Version": API_VERSION,
            },
        )
        try:
            response = self._opener.open(request, timeout=20)
            final_url = response.geturl()
            if final_url != url:
                governor.reject("GitHub response redirected outside the exact endpoint")
            status = getattr(response, "status", None)
            if status != 200:
                governor.reject(f"GitHub GET returned HTTP {status}")
            request_id = response.headers.get("X-GitHub-Request-Id")
            governor.nonempty_string(request_id, "GitHub X-GitHub-Request-Id", 200)
            payload = response.read(MAX_RESPONSE_BYTES + 1)
            if len(payload) > MAX_RESPONSE_BYTES:
                governor.reject("GitHub response exceeds the bounded size")
            decoded = json.loads(payload.decode("utf-8"))
        except governor.Rejected:
            raise
        except (urllib.error.URLError, UnicodeDecodeError, json.JSONDecodeError, OSError) as exc:
            governor.reject(f"authenticated GitHub GET failed: {type(exc).__name__}")
        return mapping(decoded, "GitHub response"), {"request_id": request_id}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN", "")
    try:
        client = GitHubGetClient(token)
        result = collect(client.fetch, dt.datetime.now(dt.timezone.utc))
        # Collection success is distinct from merge eligibility. A truthful
        # UNPROVEN assessment is successful observation, not a CI failure.
        status = 0
    except (governor.Rejected, ValueError) as exc:
        result = {"decision": "UNPROVEN", "reason": str(exc)}
        status = 2
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    args.output.write_text(payload, encoding="utf-8")
    sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    raise SystemExit(status)


if __name__ == "__main__":
    main()
