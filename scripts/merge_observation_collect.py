#!/usr/bin/env python3
"""Build a fail-closed Merge Governor observation from trusted GitHub snapshots.

This module is intentionally offline and read-only. A trusted-base workflow is
responsible for fetching complete authenticated GitHub API pages and storing the
result as the snapshot consumed here. The collector never receives a token,
contacts GitHub, executes candidate code, publishes, or merges.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

from merge_governor import (
    Rejected,
    canonical_path,
    exact_keys,
    load_json,
    nonempty_string,
    policy_digest,
    positive_int,
    reject,
    sha,
    token,
    validate_policy,
    validate_task,
    validate_workflow_path,
)


SNAPSHOT_SCHEMA = "polacore.github-merge-snapshot/v1"
TASK_SCHEMA = "polacore.merge-task-manifest/v1"
SNAPSHOT_KEYS = {
    "schema",
    "repository",
    "pull_request",
    "current_base",
    "base_commit",
    "head_commit",
    "files",
    "base_tree",
    "head_tree",
    "workflow_runs",
    "jobs",
    "reviews",
    "review_threads",
}
TASK_MANIFEST_KEYS = {
    "schema",
    "repository",
    "pull_request",
    "source_issue",
    "assurance",
    "authorized_paths",
    "acceptance_commands",
    "checks",
    "verdicts",
}
CHECK_RULE_KEYS = {"name", "kind", "workflow", "workflow_path", "job_name"}
VERDICT_RULE_KEYS = {"role", "workflow", "workflow_path", "job_name"}
PAGE_KEYS = {"complete", "items"}
JOBS_KEYS = {"complete", "by_run"}
ALLOWED_FILE_STATUSES = {
    "added": "ADDED",
    "modified": "MODIFIED",
    "removed": "DELETED",
}


def mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        reject(f"{label} must be an object")
    return value


def sequence(value: Any, label: str, limit: int) -> list[Any]:
    if not isinstance(value, list) or len(value) > limit:
        reject(f"{label} must be a list of at most {limit} items")
    return value


def field(value: Any, name: str, label: str) -> Any:
    obj = mapping(value, label)
    if name not in obj:
        reject(f"{label}.{name} is missing")
    return obj[name]


def complete_page(value: Any, label: str, limit: int) -> list[Any]:
    page = exact_keys(value, PAGE_KEYS, label)
    if page["complete"] is not True:
        reject(f"{label} is incomplete or ambiguously paginated")
    return sequence(page["items"], f"{label}.items", limit)


def validate_manifest(policy: dict[str, Any], manifest: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    exact_keys(manifest, TASK_MANIFEST_KEYS, "task manifest")
    if manifest["schema"] != TASK_SCHEMA:
        reject("unsupported task manifest schema")
    if manifest["repository"] != policy["repository"]:
        reject("task manifest repository does not match trusted policy")
    positive_int(manifest["pull_request"], "task manifest.pull_request")
    assurance = token(manifest["assurance"], "task manifest.assurance")
    if assurance not in policy["profiles"] and assurance not in policy["non_autonomous_profiles"]:
        reject("task manifest names an unknown assurance profile")

    task = {
        "source_issue": manifest["source_issue"],
        "authorized_paths": manifest["authorized_paths"],
        "acceptance_commands": manifest["acceptance_commands"],
    }
    validate_task(task, "task manifest task")

    checks_raw = sequence(manifest["checks"], "task manifest.checks", 100)
    verdicts_raw = sequence(manifest["verdicts"], "task manifest.verdicts", 20)
    if not checks_raw or not verdicts_raw:
        reject("task manifest must require deterministic checks and independent verdicts")

    checks: list[dict[str, Any]] = []
    verdicts: list[dict[str, Any]] = []
    check_names: set[str] = set()
    roles: set[str] = set()
    job_identities: set[tuple[str, str, str]] = set()

    for index, raw in enumerate(checks_raw):
        item = exact_keys(raw, CHECK_RULE_KEYS, f"task manifest.checks[{index}]")
        name = nonempty_string(item["name"], f"task manifest.checks[{index}].name", 200)
        if name in check_names:
            reject("task manifest contains duplicate check names")
        check_names.add(name)
        token(item["kind"], f"task manifest.checks[{index}].kind")
        checks.append(_validate_evidence_identity(item, f"task manifest.checks[{index}]", job_identities))

    for index, raw in enumerate(verdicts_raw):
        item = exact_keys(raw, VERDICT_RULE_KEYS, f"task manifest.verdicts[{index}]")
        role = token(item["role"], f"task manifest.verdicts[{index}].role")
        if role in roles:
            reject("task manifest contains duplicate verdict roles")
        roles.add(role)
        verdicts.append(_validate_evidence_identity(item, f"task manifest.verdicts[{index}]", job_identities))

    for acceptance in task["acceptance_commands"]:
        if acceptance["check"] not in check_names:
            reject("task acceptance command is not bound to a declared check rule")
    required_kinds = set(policy["profiles"].get(assurance, {}).get("required_check_kinds", []))
    required_roles = set(policy["profiles"].get(assurance, {}).get("required_verdict_roles", []))
    if not required_kinds.issubset({entry["kind"] for entry in checks}):
        reject("task manifest omits assurance-required check kinds")
    if not required_roles.issubset({entry["role"] for entry in verdicts}):
        reject("task manifest omits assurance-required verdict roles")
    return task, checks, verdicts


def _validate_evidence_identity(
    item: dict[str, Any], label: str, seen: set[tuple[str, str, str]]
) -> dict[str, Any]:
    workflow = nonempty_string(item["workflow"], f"{label}.workflow", 200)
    workflow_path = validate_workflow_path(item["workflow_path"], f"{label}.workflow_path")
    job_name = nonempty_string(item["job_name"], f"{label}.job_name", 150)
    if "/ pr " in job_name or "/ head " in job_name or any(ord(c) < 32 for c in job_name):
        reject(f"{label}.job_name contains reserved framing")
    identity = (workflow, workflow_path, job_name)
    if identity in seen:
        reject("task manifest reuses one evidence job identity")
    seen.add(identity)
    return item


def commit_tree_sha(commit: Any, expected_sha: str, label: str) -> str:
    if sha(field(commit, "sha", label), f"{label}.sha") != expected_sha:
        reject(f"{label} is bound to another commit")
    commit_data = field(commit, "commit", label)
    tree = field(commit_data, "tree", f"{label}.commit")
    return sha(field(tree, "sha", f"{label}.commit.tree"), f"{label}.commit.tree.sha")


def tree_map(tree: Any, expected_root: str, label: str) -> dict[str, tuple[str, str, str]]:
    obj = mapping(tree, label)
    if sha(field(obj, "sha", label), f"{label}.sha") != expected_root:
        reject(f"{label} root does not match the authenticated commit")
    if field(obj, "truncated", label) is not False:
        reject(f"{label} is truncated or incomplete")
    entries = sequence(field(obj, "tree", label), f"{label}.tree", 100_000)
    result: dict[str, tuple[str, str, str]] = {}
    for index, raw in enumerate(entries):
        entry = mapping(raw, f"{label}.tree[{index}]")
        path = canonical_path(field(entry, "path", f"{label}.tree[{index}]"), f"{label}.tree[{index}].path")
        kind = nonempty_string(field(entry, "type", f"{label}.tree[{index}]"), f"{label}.tree[{index}].type", 20)
        if kind == "tree":
            continue
        if kind not in {"blob", "commit"}:
            reject(f"{label}.tree[{index}] has unsupported Git object type")
        mode = nonempty_string(field(entry, "mode", f"{label}.tree[{index}]"), f"{label}.tree[{index}].mode", 10)
        object_sha = sha(field(entry, "sha", f"{label}.tree[{index}]"), f"{label}.tree[{index}].sha")
        if path in result:
            reject(f"{label} contains duplicate path {path}")
        result[path] = (mode, kind, object_sha)
    return result


def collect_changes(
    files_page: Any,
    base: dict[str, tuple[str, str, str]],
    head: dict[str, tuple[str, str, str]],
) -> list[dict[str, Any]]:
    files = complete_page(files_page, "snapshot.files", 500)
    api_status: dict[str, str] = {}
    for index, raw in enumerate(files):
        item = mapping(raw, f"snapshot.files.items[{index}]")
        path = canonical_path(field(item, "filename", f"snapshot.files.items[{index}]"), f"snapshot.files.items[{index}].filename")
        status = nonempty_string(field(item, "status", f"snapshot.files.items[{index}]"), f"snapshot.files.items[{index}].status", 30)
        if status not in ALLOWED_FILE_STATUSES:
            reject("renamed, copied, changed, or unknown GitHub file statuses are unsupported")
        if item.get("previous_filename") is not None:
            reject("previous_filename is forbidden because v1 does not normalize renames")
        if path in api_status:
            reject("snapshot.files contains duplicate paths")
        api_status[path] = ALLOWED_FILE_STATUSES[status]

    delta: dict[str, str] = {}
    for path in sorted(set(base) | set(head)):
        old = base.get(path)
        new = head.get(path)
        if old is None:
            delta[path] = "ADDED"
        elif new is None:
            delta[path] = "DELETED"
        elif old != new:
            delta[path] = "MODIFIED"
    if api_status != delta:
        missing = sorted(set(delta) - set(api_status))
        extra = sorted(set(api_status) - set(delta))
        mismatched = sorted(path for path in set(api_status) & set(delta) if api_status[path] != delta[path])
        reject(f"GitHub file page/tree delta mismatch; missing={missing}, extra={extra}, status={mismatched}")
    if not delta:
        reject("candidate has no changed Git object")

    changes: list[dict[str, Any]] = []
    for path, status in sorted(delta.items()):
        old = base.get(path)
        new = head.get(path)
        changes.append(
            {
                "path": path,
                "status": status,
                "old_mode": old[0] if old else None,
                "new_mode": new[0] if new else None,
            }
        )
    return changes


def collect_evidence(
    runs_page: Any,
    jobs_page: Any,
    check_rules: list[dict[str, Any]],
    verdict_rules: list[dict[str, Any]],
    base_sha: str,
    head_sha: str,
    pr_number: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    runs = complete_page(runs_page, "snapshot.workflow_runs", 500)
    jobs = exact_keys(jobs_page, JOBS_KEYS, "snapshot.jobs")
    if jobs["complete"] is not True:
        reject("snapshot.jobs is incomplete or ambiguously paginated")
    by_run = mapping(jobs["by_run"], "snapshot.jobs.by_run")

    parsed_runs: list[dict[str, Any]] = []
    seen_run_ids: set[int] = set()
    for index, raw in enumerate(runs):
        run = mapping(raw, f"snapshot.workflow_runs.items[{index}]")
        run_id = positive_int(field(run, "id", f"snapshot.workflow_runs.items[{index}]"), f"run[{index}].id")
        if run_id in seen_run_ids:
            reject("snapshot.workflow_runs contains duplicate run IDs")
        seen_run_ids.add(run_id)
        parsed_runs.append(run)

    used_jobs: set[int] = set()

    def resolve(rule: dict[str, Any], label: str) -> tuple[int, int]:
        expected_job = f"{rule['job_name']} / pr {pr_number} / head {head_sha}"
        matches: list[tuple[int, int, dict[str, Any], dict[str, Any]]] = []
        for run in parsed_runs:
            if run.get("name") != rule["workflow"] or run.get("path") != rule["workflow_path"]:
                continue
            if run.get("event") != "pull_request_target" or run.get("head_sha") != base_sha:
                continue
            run_id = positive_int(run.get("id"), f"{label} run id")
            jobs_for_run = by_run.get(str(run_id))
            if jobs_for_run is None:
                reject(f"snapshot.jobs has no complete page for required run {run_id}")
            for raw_job in complete_page(jobs_for_run, f"snapshot.jobs.by_run.{run_id}", 500):
                job = mapping(raw_job, f"snapshot.jobs.by_run.{run_id} item")
                if job.get("name") == expected_job:
                    job_id = positive_int(job.get("id"), f"{label} job id")
                    matches.append((run_id, job_id, run, job))
        if len(matches) != 1:
            reject(f"{label} evidence identity resolved to {len(matches)} jobs instead of exactly one")
        run_id, job_id, run, job = matches[0]
        if job_id in used_jobs:
            reject("one GitHub job cannot satisfy multiple independent evidence requirements")
        used_jobs.add(job_id)
        if run.get("status") != "completed" or run.get("conclusion") != "success":
            reject(f"{label} workflow run is pending, skipped, cancelled, or failing")
        positive_int(run.get("run_attempt"), f"{label} run_attempt")
        if job.get("status") != "completed" or job.get("conclusion") != "success":
            reject(f"{label} job is pending, skipped, cancelled, or failing")
        return run_id, job_id

    checks: list[dict[str, Any]] = []
    verdicts: list[dict[str, Any]] = []
    for index, rule in enumerate(check_rules):
        run_id, job_id = resolve(rule, f"check[{index}]")
        checks.append(
            {
                "name": rule["name"],
                "kind": rule["kind"],
                "workflow": rule["workflow"],
                "workflow_path": rule["workflow_path"],
                "workflow_sha": base_sha,
                "run_id": run_id,
                "job_id": job_id,
                "head_sha": head_sha,
                "conclusion": "PASS",
            }
        )
    for index, rule in enumerate(verdict_rules):
        run_id, job_id = resolve(rule, f"verdict[{index}]")
        verdicts.append(
            {
                "role": rule["role"],
                "workflow": rule["workflow"],
                "workflow_path": rule["workflow_path"],
                "workflow_sha": base_sha,
                "run_id": run_id,
                "job_id": job_id,
                "head_sha": head_sha,
                "verdict": "NON_BLOCKING",
                "independent": True,
            }
        )
    return checks, verdicts


def collect(policy: dict[str, Any], manifest: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    validate_policy(policy)
    task, check_rules, verdict_rules = validate_manifest(policy, manifest)
    exact_keys(snapshot, SNAPSHOT_KEYS, "snapshot")
    if snapshot["schema"] != SNAPSHOT_SCHEMA:
        reject("unsupported GitHub snapshot schema")
    if snapshot["repository"] != policy["repository"]:
        reject("snapshot repository does not match trusted policy")

    pr = mapping(snapshot["pull_request"], "snapshot.pull_request")
    pr_number = positive_int(field(pr, "number", "snapshot.pull_request"), "snapshot.pull_request.number")
    if pr_number != manifest["pull_request"]:
        reject("snapshot pull request does not match trusted task manifest")
    base = mapping(field(pr, "base", "snapshot.pull_request"), "snapshot.pull_request.base")
    head = mapping(field(pr, "head", "snapshot.pull_request"), "snapshot.pull_request.head")
    base_ref = nonempty_string(field(base, "ref", "snapshot.pull_request.base"), "snapshot.pull_request.base.ref", 100)
    base_sha = sha(field(base, "sha", "snapshot.pull_request.base"), "snapshot.pull_request.base.sha")
    base_repo = field(
        mapping(field(base, "repo", "snapshot.pull_request.base"), "snapshot.pull_request.base.repo"),
        "full_name",
        "snapshot.pull_request.base.repo",
    )
    if nonempty_string(base_repo, "snapshot.pull_request.base.repo.full_name", 200) != policy["repository"]:
        reject("pull-request base repository does not match trusted policy")
    head_ref = nonempty_string(field(head, "ref", "snapshot.pull_request.head"), "snapshot.pull_request.head.ref", 250)
    head_sha = sha(field(head, "sha", "snapshot.pull_request.head"), "snapshot.pull_request.head.sha")
    head_repo = field(mapping(field(head, "repo", "snapshot.pull_request.head"), "snapshot.pull_request.head.repo"), "full_name", "snapshot.pull_request.head.repo")
    nonempty_string(head_repo, "snapshot.pull_request.head.repo.full_name", 200)

    current_base = mapping(snapshot["current_base"], "snapshot.current_base")
    if field(current_base, "name", "snapshot.current_base") != policy["integration_branch"]:
        reject("snapshot.current_base is not engineering")
    current_base_sha = sha(
        field(mapping(field(current_base, "commit", "snapshot.current_base"), "snapshot.current_base.commit"), "sha", "snapshot.current_base.commit"),
        "snapshot.current_base.commit.sha",
    )

    base_tree_sha = commit_tree_sha(snapshot["base_commit"], base_sha, "snapshot.base_commit")
    head_tree_sha = commit_tree_sha(snapshot["head_commit"], head_sha, "snapshot.head_commit")
    base_tree = tree_map(snapshot["base_tree"], base_tree_sha, "snapshot.base_tree")
    head_tree = tree_map(snapshot["head_tree"], head_tree_sha, "snapshot.head_tree")
    changes = collect_changes(snapshot["files"], base_tree, head_tree)
    checks, verdicts = collect_evidence(
        snapshot["workflow_runs"], snapshot["jobs"], check_rules, verdict_rules, base_sha, head_sha, pr_number
    )

    reviews = complete_page(snapshot["reviews"], "snapshot.reviews", 500)
    contradictory: list[str] = []
    for index, raw in enumerate(reviews):
        review = mapping(raw, f"snapshot.reviews.items[{index}]")
        if review.get("state") == "CHANGES_REQUESTED" and review.get("commit_id") in {None, head_sha}:
            contradictory.append(f"blocking review {positive_int(review.get('id'), 'blocking review id')}")

    threads = complete_page(snapshot["review_threads"], "snapshot.review_threads", 500)
    unresolved = 0
    for index, raw in enumerate(threads):
        thread = mapping(raw, f"snapshot.review_threads.items[{index}]")
        resolved = field(thread, "isResolved", f"snapshot.review_threads.items[{index}]")
        if not isinstance(resolved, bool):
            reject("review thread resolution state is ambiguous")
        unresolved += int(not resolved)

    state = field(pr, "state", "snapshot.pull_request")
    draft = field(pr, "draft", "snapshot.pull_request")
    mergeable = field(pr, "mergeable", "snapshot.pull_request")
    merged = field(pr, "merged", "snapshot.pull_request")
    if state != "open":
        reject("v1 collector accepts open pull requests only")
    if (
        not isinstance(draft, bool)
        or (mergeable is not True and mergeable is not False and mergeable is not None)
        or not isinstance(merged, bool)
    ):
        reject("pull-request draft/mergeable/merged state has invalid type")
    if merged:
        reject("v1 collector accepts open candidates only; replay requires a trusted merge record")

    return {
        "schema": "polacore.merge-observation/v1",
        "repository": snapshot["repository"],
        "pull_request": pr_number,
        "base_ref": base_ref,
        "base_sha": base_sha,
        "current_engineering_sha": current_base_sha,
        "head_repo": head_repo,
        "head_ref": head_ref,
        "head_sha": head_sha,
        "head_sha_kind": "PULL_REQUEST_HEAD",
        "assurance": manifest["assurance"],
        "task": task,
        "changes": changes,
        "checks": checks,
        "verdicts": verdicts,
        "policy_version": policy["version"],
        "policy_sha256": policy_digest(policy),
        "unresolved_review_threads": unresolved,
        "contradictory_evidence": contradictory,
        "draft": draft,
        "mergeable": mergeable,
        "protection_bypass_requested": False,
        "merge": {"state": "OPEN"},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", required=True, type=pathlib.Path)
    parser.add_argument("--task", required=True, type=pathlib.Path)
    parser.add_argument("--snapshot", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        result = collect(load_json(args.policy), load_json(args.task), load_json(args.snapshot))
        status = 0
    except (Rejected, ValueError) as exc:
        result = {"decision": "UNPROVEN", "reason": str(exc)}
        status = 1
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    raise SystemExit(status)


if __name__ == "__main__":
    main()
