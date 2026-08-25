#!/usr/bin/env python3
"""Fail-closed decision core for PolaCore engineering merge certificates.

The program is deliberately pure: it never calls GitHub, executes acceptance
commands, publishes, or merges. A separate privileged controller must build the
trusted observation from GitHub, load this code and policy from the protected
``engineering`` base, and act only on an ``ELIGIBLE`` decision for the same
unchanged pull-request head.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any


POLICY_KEYS = {
    "schema",
    "version",
    "repository",
    "integration_branch",
    "authorized_head_prefixes",
    "assurance_order",
    "non_autonomous_profiles",
    "profiles",
    "path_assurance_floors",
    "forbidden_exact_paths",
    "forbidden_path_prefixes",
    "trusted_gate_paths",
}
CERTIFICATE_KEYS = {
    "schema",
    "repository",
    "pull_request",
    "base_ref",
    "base_sha",
    "head_repo",
    "head_ref",
    "head_sha",
    "assurance",
    "task",
    "changes",
    "checks",
    "verdicts",
    "policy_version",
    "policy_sha256",
}
OBSERVATION_KEYS = {
    "schema",
    "repository",
    "pull_request",
    "base_ref",
    "base_sha",
    "current_engineering_sha",
    "head_repo",
    "head_ref",
    "head_sha",
    "head_sha_kind",
    "assurance",
    "task",
    "changes",
    "checks",
    "verdicts",
    "policy_version",
    "policy_sha256",
    "unresolved_review_threads",
    "contradictory_evidence",
    "draft",
    "mergeable",
    "protection_bypass_requested",
    "merge",
}
TASK_KEYS = {"source_issue", "authorized_paths", "acceptance_commands"}
ACCEPTANCE_KEYS = {"command", "check"}
CHANGE_KEYS = {"path", "status", "old_mode", "new_mode"}
CHECK_KEYS = {
    "name",
    "kind",
    "workflow",
    "workflow_path",
    "workflow_sha",
    "run_id",
    "job_id",
    "head_sha",
    "conclusion",
}
VERDICT_KEYS = {
    "role",
    "workflow",
    "workflow_path",
    "workflow_sha",
    "run_id",
    "job_id",
    "head_sha",
    "verdict",
    "independent",
}
PROFILE_KEYS = {"required_check_kinds", "required_verdict_roles"}
FLOOR_KEYS = {"pattern", "profile"}
OPEN_MERGE_KEYS = {"state"}
MERGED_MERGE_KEYS = {"state", "head_sha", "merge_sha", "certificate_sha256"}

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
TOKEN_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
POLICY_SCHEMA = "polacore.merge-governor-policy/v1"
CERTIFICATE_SCHEMA = "polacore.merge-certificate/v1"
OBSERVATION_SCHEMA = "polacore.merge-observation/v1"


class Rejected(ValueError):
    """The supplied evidence cannot establish merge eligibility."""


def reject(message: str) -> None:
    raise Rejected(message)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            reject(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        reject(f"cannot read strict JSON {path}: {exc}")
    if not isinstance(value, dict):
        reject(f"top-level JSON in {path} must be an object")
    return value


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        reject(f"{label} must be an object")
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        reject(f"{label} keys mismatch; missing={missing}, extra={extra}")
    return value


def nonempty_string(value: Any, label: str, limit: int = 500) -> str:
    if not isinstance(value, str) or not value or len(value) > limit:
        reject(f"{label} must be a non-empty string of at most {limit} characters")
    if "\x00" in value:
        reject(f"{label} contains NUL")
    return value


def positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        reject(f"{label} must be a positive integer")
    return value


def sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        reject(f"{label} must be a lowercase 40-hex commit SHA")
    return value


def token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not TOKEN_RE.fullmatch(value):
        reject(f"{label} must be an uppercase policy token")
    return value


def string_list(value: Any, label: str, *, nonempty: bool = True) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value) or len(value) > 200:
        reject(f"{label} must be a bounded{' non-empty' if nonempty else ''} list")
    result = [nonempty_string(item, f"{label} item", 500) for item in value]
    if len(result) != len(set(result)):
        reject(f"{label} contains duplicates")
    return result


def canonical_path(value: Any, label: str, *, allow_pattern: bool = False) -> str:
    path = nonempty_string(value, label, 300)
    if any(ord(character) < 32 or ord(character) == 127 for character in path):
        reject(f"{label} contains control characters")
    suffix = "/**" if allow_pattern and path.endswith("/**") else ""
    base = path[:-3] if suffix else path
    if not base or base.startswith("/") or base.endswith("/") or "\\" in base:
        reject(f"{label} is not a canonical repository-relative path")
    parts = base.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        reject(f"{label} is not a canonical repository-relative path")
    if "*" in base or "?" in base or "[" in base:
        reject(f"{label} has unsupported pattern syntax")
    return base + suffix


def validate_workflow_path(value: Any, label: str) -> str:
    path = canonical_path(value, label)
    if not path.startswith(".github/workflows/") or not path.endswith((".yml", ".yaml")):
        reject(f"{label} is not a GitHub Actions workflow")
    return path


def pattern_matches(pattern: str, path: str) -> bool:
    if pattern.endswith("/**"):
        base = pattern[:-3]
        return path == base or path.startswith(base + "/")
    return path == pattern


def policy_digest(policy: dict[str, Any]) -> str:
    return digest(policy)


def validate_policy(policy: dict[str, Any]) -> None:
    exact_keys(policy, POLICY_KEYS, "policy")
    if policy["schema"] != POLICY_SCHEMA:
        reject("unsupported policy schema")
    nonempty_string(policy["version"], "policy.version", 100)
    if nonempty_string(policy["repository"], "policy.repository", 200) != "djibian/polacore":
        reject("v1 policy repository may not change")
    if nonempty_string(policy["integration_branch"], "policy.integration_branch", 100) != "engineering":
        reject("v1 autonomous integration branch must remain engineering")

    prefixes = string_list(policy["authorized_head_prefixes"], "policy.authorized_head_prefixes")
    if any(prefix.startswith("refs/") or ".." in prefix or not prefix.endswith(("/", "-")) for prefix in prefixes):
        reject("authorized head prefixes must be plain branch prefixes ending in '/' or '-'")

    assurance_order = string_list(policy["assurance_order"], "policy.assurance_order")
    if assurance_order != ["STANDARD", "REINFORCED", "CONSTITUTIONAL"]:
        reject("policy assurance order must preserve the PolaCore v1 order")
    non_autonomous = string_list(policy["non_autonomous_profiles"], "policy.non_autonomous_profiles")
    if "OBJECTIVE_AMENDMENT" not in non_autonomous:
        reject("OBJECTIVE_AMENDMENT must remain non-autonomous")

    profiles = policy["profiles"]
    if not isinstance(profiles, dict) or set(profiles) != set(assurance_order):
        reject("policy profiles must exactly match assurance_order")
    for name, profile in profiles.items():
        exact_keys(profile, PROFILE_KEYS, f"policy.profiles.{name}")
        kinds = string_list(profile["required_check_kinds"], f"{name}.required_check_kinds")
        roles = string_list(profile["required_verdict_roles"], f"{name}.required_verdict_roles")
        for kind in kinds:
            token(kind, f"{name} check kind")
        for role in roles:
            token(role, f"{name} verdict role")

    floors = policy["path_assurance_floors"]
    if not isinstance(floors, list) or len(floors) > 100:
        reject("policy.path_assurance_floors must be a bounded list")
    seen_patterns: set[str] = set()
    for index, floor in enumerate(floors):
        exact_keys(floor, FLOOR_KEYS, f"path_assurance_floors[{index}]")
        pattern = canonical_path(floor["pattern"], f"path_assurance_floors[{index}].pattern", allow_pattern=True)
        if pattern in seen_patterns:
            reject("duplicate path assurance floor")
        seen_patterns.add(pattern)
        if floor["profile"] not in assurance_order:
            reject("path assurance floor names an unknown profile")

    exact = [canonical_path(x, "forbidden exact path") for x in string_list(policy["forbidden_exact_paths"], "policy.forbidden_exact_paths")]
    path_prefixes = string_list(policy["forbidden_path_prefixes"], "policy.forbidden_path_prefixes")
    for prefix in path_prefixes:
        if prefix.startswith("/") or "\\" in prefix or "*" in prefix or "?" in prefix or "[" in prefix:
            reject("forbidden path prefixes must be plain repository-relative string prefixes")
        if any(part in {".", ".."} for part in prefix.rstrip("/").split("/")):
            reject("forbidden path prefixes may not traverse directories")
    trusted = [canonical_path(x, "trusted gate path") for x in string_list(policy["trusted_gate_paths"], "policy.trusted_gate_paths")]
    for path in trusted:
        if path not in exact and not any(path.startswith(prefix) for prefix in path_prefixes):
            reject(f"trusted gate path is not forbidden to candidates: {path}")


def validate_task(task: Any, label: str) -> dict[str, Any]:
    result = exact_keys(task, TASK_KEYS, label)
    positive_int(result["source_issue"], f"{label}.source_issue")
    authorized = result["authorized_paths"]
    if not isinstance(authorized, list) or not authorized or len(authorized) > 100:
        reject(f"{label}.authorized_paths must be a bounded non-empty list")
    normalized = [canonical_path(x, f"{label}.authorized_paths", allow_pattern=True) for x in authorized]
    if len(normalized) != len(set(normalized)):
        reject(f"{label}.authorized_paths contains duplicates")

    commands = result["acceptance_commands"]
    if not isinstance(commands, list) or not commands or len(commands) > 50:
        reject(f"{label}.acceptance_commands must be a bounded non-empty list")
    seen_commands: set[str] = set()
    for index, entry in enumerate(commands):
        exact_keys(entry, ACCEPTANCE_KEYS, f"{label}.acceptance_commands[{index}]")
        command = nonempty_string(entry["command"], f"{label} acceptance command", 1000)
        if "\n" in command or "\r" in command:
            reject(f"{label} acceptance commands must be single-line data")
        nonempty_string(entry["check"], f"{label} acceptance check", 200)
        if command in seen_commands:
            reject(f"{label}.acceptance_commands contains duplicates")
        seen_commands.add(command)
    return result


def validate_checks(
    entries: Any, expected_head: str, expected_workflow_sha: str, label: str
) -> list[dict[str, Any]]:
    if not isinstance(entries, list) or not entries or len(entries) > 100:
        reject(f"{label} must be a bounded non-empty list")
    names: set[str] = set()
    job_ids: set[int] = set()
    result: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        item = exact_keys(entry, CHECK_KEYS, f"{label}[{index}]")
        name = nonempty_string(item["name"], f"{label}[{index}].name", 200)
        if name in names:
            reject(f"{label} contains duplicate check names")
        names.add(name)
        token(item["kind"], f"{label}[{index}].kind")
        nonempty_string(item["workflow"], f"{label}[{index}].workflow", 200)
        validate_workflow_path(item["workflow_path"], f"{label}[{index}].workflow_path")
        if sha(item["workflow_sha"], f"{label}[{index}].workflow_sha") != expected_workflow_sha:
            reject(f"{label}[{index}] used candidate-controlled or stale workflow code")
        positive_int(item["run_id"], f"{label}[{index}].run_id")
        job_id = positive_int(item["job_id"], f"{label}[{index}].job_id")
        if job_id in job_ids:
            reject(f"{label} contains duplicate evidence job IDs")
        job_ids.add(job_id)
        if sha(item["head_sha"], f"{label}[{index}].head_sha") != expected_head:
            reject(f"{label}[{index}] is stale or bound to another head")
        if item["conclusion"] != "PASS":
            reject(f"{label}[{index}] is missing, skipped, ambiguous, or non-passing")
        result.append(item)
    return result


def validate_changes(entries: Any, label: str) -> list[str]:
    """Validate an exact Git diff inventory and return its sorted paths.

    V1 deliberately accepts only ordinary blobs. Renames/copies must remain
    explicit unsupported statuses rather than being normalized in a way that
    could hide a protected old path.
    """

    if not isinstance(entries, list) or not entries or len(entries) > 500:
        reject(f"{label} must be a bounded non-empty list")
    paths: list[str] = []
    allowed_modes = {"100644", "100755"}
    for index, entry in enumerate(entries):
        item = exact_keys(entry, CHANGE_KEYS, f"{label}[{index}]")
        path = canonical_path(item["path"], f"{label}[{index}].path")
        status = item["status"]
        old_mode = item["old_mode"]
        new_mode = item["new_mode"]
        if status == "ADDED":
            if old_mode is not None or new_mode not in allowed_modes:
                reject(f"{label}[{index}] is not an ordinary added blob")
        elif status == "MODIFIED":
            if old_mode not in allowed_modes or new_mode not in allowed_modes:
                reject(f"{label}[{index}] is not an ordinary modified blob")
        elif status == "DELETED":
            if old_mode not in allowed_modes or new_mode is not None:
                reject(f"{label}[{index}] is not an ordinary deleted blob")
        else:
            reject(f"{label}[{index}] has unsupported or ambiguous Git status")
        paths.append(path)
    if len(paths) != len(set(paths)):
        reject(f"{label} contains duplicate paths")
    if paths != sorted(paths):
        reject(f"{label} must be sorted by path for an unambiguous certificate")
    return paths


def validate_verdicts(
    entries: Any, expected_head: str, expected_workflow_sha: str, label: str
) -> list[dict[str, Any]]:
    if not isinstance(entries, list) or not entries or len(entries) > 20:
        reject(f"{label} must be a bounded non-empty list")
    roles: set[str] = set()
    job_ids: set[int] = set()
    result: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        item = exact_keys(entry, VERDICT_KEYS, f"{label}[{index}]")
        role = token(item["role"], f"{label}[{index}].role")
        if role in roles:
            reject(f"{label} contains duplicate verdict roles")
        roles.add(role)
        nonempty_string(item["workflow"], f"{label}[{index}].workflow", 200)
        validate_workflow_path(item["workflow_path"], f"{label}[{index}].workflow_path")
        if sha(item["workflow_sha"], f"{label}[{index}].workflow_sha") != expected_workflow_sha:
            reject(f"{label}[{index}] used candidate-controlled or stale workflow code")
        positive_int(item["run_id"], f"{label}[{index}].run_id")
        job_id = positive_int(item["job_id"], f"{label}[{index}].job_id")
        if job_id in job_ids:
            reject(f"{label} contains duplicate verdict job IDs")
        job_ids.add(job_id)
        if sha(item["head_sha"], f"{label}[{index}].head_sha") != expected_head:
            reject(f"{label}[{index}] is stale or bound to another head")
        if item["independent"] is not True:
            reject(f"{label}[{index}] is not established as independent")
        if item["verdict"] != "NON_BLOCKING":
            reject(f"{label}[{index}] is blocking or ambiguous")
        result.append(item)
    return result


def required_assurance(policy: dict[str, Any], paths: list[str]) -> str:
    order = policy["assurance_order"]
    rank = 0
    for floor in policy["path_assurance_floors"]:
        if any(pattern_matches(floor["pattern"], path) for path in paths):
            rank = max(rank, order.index(floor["profile"]))
    return order[rank]


def is_forbidden(policy: dict[str, Any], path: str) -> bool:
    return path in policy["forbidden_exact_paths"] or any(
        path.startswith(prefix) for prefix in policy["forbidden_path_prefixes"]
    )


def compare_bound_field(certificate: dict[str, Any], observation: dict[str, Any], field: str) -> None:
    if certificate[field] != observation[field]:
        reject(f"certificate/observation mismatch for {field}")


def evaluate(policy: dict[str, Any], certificate: dict[str, Any], observation: dict[str, Any]) -> dict[str, Any]:
    """Return an auditable decision or raise :class:`Rejected`."""

    validate_policy(policy)
    exact_keys(certificate, CERTIFICATE_KEYS, "certificate")
    exact_keys(observation, OBSERVATION_KEYS, "observation")
    if certificate["schema"] != CERTIFICATE_SCHEMA:
        reject("unsupported certificate schema")
    if observation["schema"] != OBSERVATION_SCHEMA:
        reject("unsupported observation schema")

    for field in (
        "repository",
        "pull_request",
        "base_ref",
        "base_sha",
        "head_repo",
        "head_ref",
        "head_sha",
        "assurance",
        "task",
        "changes",
        "checks",
        "verdicts",
        "policy_version",
        "policy_sha256",
    ):
        compare_bound_field(certificate, observation, field)

    repository = nonempty_string(certificate["repository"], "certificate.repository", 200)
    if repository != policy["repository"]:
        reject("repository is outside trusted policy")
    positive_int(certificate["pull_request"], "certificate.pull_request")
    if certificate["base_ref"] != policy["integration_branch"]:
        reject("base branch is not the autonomous integration branch")
    base_sha = sha(certificate["base_sha"], "certificate.base_sha")
    head_sha = sha(certificate["head_sha"], "certificate.head_sha")
    if base_sha == head_sha:
        reject("candidate head must differ from its base")
    if certificate["head_repo"] != repository:
        reject("fork pull requests are not eligible")
    head_ref = nonempty_string(certificate["head_ref"], "certificate.head_ref", 250)
    if not any(head_ref.startswith(prefix) for prefix in policy["authorized_head_prefixes"]):
        reject("head branch is outside the authorized agent namespace")
    if observation["head_sha_kind"] != "PULL_REQUEST_HEAD":
        reject("synthetic merge or unknown SHA kind is not eligible")

    assurance = token(certificate["assurance"], "certificate.assurance")
    if assurance in policy["non_autonomous_profiles"]:
        reject("objective amendments are never autonomously mergeable")
    if assurance not in policy["profiles"]:
        reject("unknown assurance profile")

    task = validate_task(certificate["task"], "certificate.task")
    validate_task(observation["task"], "observation.task")

    changed_paths = validate_changes(certificate["changes"], "certificate.changes")
    validate_changes(observation["changes"], "observation.changes")
    for path in changed_paths:
        if is_forbidden(policy, path):
            reject(f"candidate changes forbidden policy/authority path: {path}")
        if not any(pattern_matches(pattern, path) for pattern in task["authorized_paths"]):
            reject(f"changed path is outside task authority: {path}")

    order = policy["assurance_order"]
    floor = required_assurance(policy, changed_paths)
    if order.index(assurance) < order.index(floor):
        reject(f"assurance {assurance} is below deterministic path floor {floor}")

    checks = validate_checks(certificate["checks"], head_sha, base_sha, "certificate.checks")
    validate_checks(observation["checks"], head_sha, base_sha, "observation.checks")
    check_names = {entry["name"] for entry in checks}
    check_kinds = {entry["kind"] for entry in checks}
    for acceptance in task["acceptance_commands"]:
        if acceptance["check"] not in check_names:
            reject("an acceptance command is not bound to a passing deterministic check")
    required_kinds = set(policy["profiles"][assurance]["required_check_kinds"])
    if not required_kinds.issubset(check_kinds):
        reject("assurance-required deterministic check kinds are missing")

    verdicts = validate_verdicts(certificate["verdicts"], head_sha, base_sha, "certificate.verdicts")
    validate_verdicts(observation["verdicts"], head_sha, base_sha, "observation.verdicts")
    check_job_ids = {entry["job_id"] for entry in checks}
    verdict_job_ids = {entry["job_id"] for entry in verdicts}
    if check_job_ids & verdict_job_ids:
        reject("independent verdicts may not reuse deterministic-check jobs")
    roles = {entry["role"] for entry in verdicts}
    required_roles = set(policy["profiles"][assurance]["required_verdict_roles"])
    if not required_roles.issubset(roles):
        reject("assurance-required independent verdicts are missing")

    if certificate["policy_version"] != policy["version"]:
        reject("certificate policy version is stale")
    expected_policy_digest = policy_digest(policy)
    if certificate["policy_sha256"] != expected_policy_digest:
        reject("certificate policy digest is stale or mismatched")
    if sha(observation["current_engineering_sha"], "observation.current_engineering_sha") != base_sha:
        # A previously completed merge is handled below through its immutable
        # merge record. Every still-open candidate must be based on current state.
        if not isinstance(observation["merge"], dict) or observation["merge"].get("state") != "MERGED":
            reject("engineering moved after certification")

    unresolved = observation["unresolved_review_threads"]
    if isinstance(unresolved, bool) or not isinstance(unresolved, int) or unresolved < 0:
        reject("unresolved_review_threads must be a non-negative integer")
    contradictory = observation["contradictory_evidence"]
    if not isinstance(contradictory, list) or len(contradictory) > 100:
        reject("contradictory_evidence must be a bounded list")
    if unresolved:
        reject("unresolved review conversations remain")
    if contradictory:
        reject("contradictory or stale evidence remains")
    if observation["draft"] is not False:
        reject("draft or ambiguous pull-request state is not eligible")
    if observation["mergeable"] is not True:
        reject("GitHub has not established the exact candidate as mergeable")
    if observation["protection_bypass_requested"] is not False:
        reject("repository-protection bypass is forbidden")

    merge = observation["merge"]
    if not isinstance(merge, dict):
        reject("observation.merge must be an object")
    state = merge.get("state")
    certificate_digest = digest(certificate)
    if state == "MERGED":
        exact_keys(merge, MERGED_MERGE_KEYS, "observation.merge")
        if sha(merge["head_sha"], "observation.merge.head_sha") != head_sha:
            reject("merge record is bound to another candidate head")
        merge_sha = sha(merge["merge_sha"], "observation.merge.merge_sha")
        if merge["certificate_sha256"] != certificate_digest:
            reject("merge replay certificate does not match the recorded merge")
        return {
            "decision": "ALREADY_MERGED",
            "repository": repository,
            "pull_request": certificate["pull_request"],
            "head_sha": head_sha,
            "merge_sha": merge_sha,
            "certificate_sha256": certificate_digest,
            "policy_sha256": expected_policy_digest,
        }
    exact_keys(merge, OPEN_MERGE_KEYS, "observation.merge")
    if state != "OPEN":
        reject("unsupported merge state")

    return {
        "decision": "ELIGIBLE",
        "repository": repository,
        "pull_request": certificate["pull_request"],
        "base_sha": base_sha,
        "head_sha": head_sha,
        "assurance": assurance,
        "certificate_sha256": certificate_digest,
        "policy_sha256": expected_policy_digest,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=pathlib.Path, required=True)
    parser.add_argument("--certificate", type=pathlib.Path, required=True)
    parser.add_argument("--observation", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()

    try:
        policy = load_json(args.policy)
        certificate = load_json(args.certificate)
        observation = load_json(args.observation)
        result = evaluate(policy, certificate, observation)
        status = 0
    except (Rejected, ValueError) as exc:
        result = {"decision": "UNPROVEN", "reason": str(exc)}
        status = 1

    payload = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    sys.stdout.write(payload)
    raise SystemExit(status)


if __name__ == "__main__":
    main()
