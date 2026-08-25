#!/usr/bin/env python3
"""Deterministically authorize only narrow PolaCore A0 repair diffs.

This file is part of the trusted A0 gate and is never in the autonomous edit
allowlist. It intentionally permits only:
- replacement of one allowlisted Albert model identifier by another;
- bounded increases of existing `timeout-minutes:` values;
- addition of the two Python bytecode ignore patterns proven necessary by #39.
Everything else escalates to a human-governed change.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

ALLOWED_MODELS = (
    "albert/deepseek-v4-flash",
    "albert/qwen3-coder-30b-A3b-instruct",
    "albert/openai/gpt-oss-120b",
)
MODEL_RE = re.compile("(" + "|".join(re.escape(x) for x in ALLOWED_MODELS) + ")")
TIMEOUT_RE = re.compile(r"^(\s*timeout-minutes:\s*)([0-9]+)(\s*)$")

ALLOWED_PATHS = {
    ".gitignore",
    "opencode.json",
    ".opencode/agents/router.md",
    ".opencode/agents/builder-canary.md",
    ".opencode/agents/reviewer-canary.md",
    ".opencode/agents/smoke.md",
    ".opencode/agents/builder-task-3d.md",
    ".opencode/agents/reviewer-task-3d.md",
    ".github/workflows/agent-router.yml",
    ".github/workflows/agent-router-contract.yml",
    ".github/workflows/agent-router-terminal-contract.yml",
    ".github/workflows/agent-builder-canary.yml",
    ".github/workflows/agent-builder-canary-contract.yml",
    ".github/workflows/agent-reviewer-canary.yml",
    ".github/workflows/agent-ci-reviewer-canary-contract.yml",
    ".github/workflows/agent-smoke.yml",
    ".github/workflows/agent-real-task-v1.yml",
    ".github/workflows/agent-real-task-v1-contract.yml",
}

EXPECTED_WORKFLOWS_BY_PATH = {
    ".gitignore": {"PolaCore Router Terminal Decision Contract"},
    "opencode.json": {"Agent Smoke - Albert + OpenCode"},
    ".opencode/agents/router.md": {"PolaCore Router Contract", "PolaCore Router Terminal Decision Contract"},
    ".opencode/agents/builder-canary.md": {"PolaCore Builder Canary Contract"},
    ".opencode/agents/reviewer-canary.md": {"PolaCore CI Reviewer Canary Contract"},
    ".opencode/agents/smoke.md": {"Agent Smoke - Albert + OpenCode"},
    ".opencode/agents/builder-task-3d.md": {"PolaCore Real Task v1 Contract"},
    ".opencode/agents/reviewer-task-3d.md": {"PolaCore Real Task v1 Contract"},
    ".github/workflows/agent-router.yml": {"PolaCore Router Contract", "PolaCore CI Reviewer Canary Contract"},
    ".github/workflows/agent-router-contract.yml": {"PolaCore Router Contract"},
    ".github/workflows/agent-router-terminal-contract.yml": {"PolaCore Router Terminal Decision Contract"},
    ".github/workflows/agent-builder-canary.yml": {"PolaCore Router Contract", "PolaCore Builder Canary Contract"},
    ".github/workflows/agent-builder-canary-contract.yml": {"PolaCore Builder Canary Contract"},
    ".github/workflows/agent-reviewer-canary.yml": {"PolaCore CI Reviewer Canary Contract"},
    ".github/workflows/agent-ci-reviewer-canary-contract.yml": {"PolaCore CI Reviewer Canary Contract"},
    ".github/workflows/agent-smoke.yml": {"Agent Smoke - Albert + OpenCode"},
    ".github/workflows/agent-real-task-v1.yml": {"PolaCore Real Task v1 Contract"},
    ".github/workflows/agent-real-task-v1-contract.yml": {"PolaCore Real Task v1 Contract"},
}


def run(*args: str) -> str:
    p = subprocess.run(args, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode:
        raise SystemExit(f"gate command failed: {' '.join(args)}\n{p.stderr}")
    return p.stdout


def normalize_model(line: str) -> tuple[str, int]:
    found = MODEL_RE.findall(line)
    return MODEL_RE.sub("albert/<MODEL>", line), len(found)


def safe_replacement(old: str, new: str) -> bool:
    old_norm, old_count = normalize_model(old)
    new_norm, new_count = normalize_model(new)
    if old_count == 1 and new_count == 1 and old_norm == new_norm and old != new:
        return True
    om = TIMEOUT_RE.match(old)
    nm = TIMEOUT_RE.match(new)
    if om and nm and om.group(1) == nm.group(1) and om.group(3) == nm.group(3):
        old_n, new_n = int(om.group(2)), int(nm.group(2))
        return 1 <= old_n <= new_n <= 20 and old_n != new_n
    return False


def parse_diff(text: str) -> dict[str, tuple[list[str], list[str]]]:
    current: str | None = None
    result: dict[str, tuple[list[str], list[str]]] = {}
    for line in text.splitlines():
        if line.startswith("diff --git a/"):
            parts = line.split()
            if len(parts) != 4 or not parts[2].startswith("a/") or not parts[3].startswith("b/"):
                raise SystemExit("malformed diff header")
            a, b = parts[2][2:], parts[3][2:]
            if a != b:
                raise SystemExit("renames are forbidden in A0")
            current = a
            result.setdefault(current, ([], []))
        elif current and line.startswith("--- "):
            continue
        elif current and line.startswith("+++ "):
            continue
        elif current and line.startswith("@@"):
            continue
        elif current and line.startswith("-"):
            result[current][0].append(line[1:])
        elif current and line.startswith("+"):
            result[current][1].append(line[1:])
    return result


def validate(base: str, head: str | None, worktree: bool) -> dict[str, object]:
    if worktree:
        status = run("git", "status", "--porcelain", "--untracked-files=all")
        if any(line.startswith("?? ") for line in status.splitlines()):
            raise SystemExit("A0 may not create untracked files")
        name_status = run("git", "diff", "--name-status")
        diff = run("git", "diff", "--unified=0", "--no-ext-diff")
    else:
        assert head is not None
        name_status = run("git", "diff", "--name-status", base, head)
        diff = run("git", "diff", "--unified=0", "--no-ext-diff", base, head)

    changed: list[str] = []
    for raw in name_status.splitlines():
        if not raw.strip():
            continue
        parts = raw.split("\t")
        if len(parts) != 2 or parts[0] != "M":
            raise SystemExit(f"A0 permits modified existing files only: {raw}")
        path = parts[1]
        if path not in ALLOWED_PATHS:
            raise SystemExit(f"path outside A0 allowlist: {path}")
        changed.append(path)
    if not changed:
        raise SystemExit("A0 repair produced no change")
    if len(changed) > 12:
        raise SystemExit("A0 repair changes too many files")

    parsed = parse_diff(diff)
    total_lines = 0
    for path in changed:
        removed, added = parsed.get(path, ([], []))
        total_lines += len(removed) + len(added)
        if path == ".gitignore":
            if removed:
                raise SystemExit("A0 may not remove ignore rules")
            if not added or any(x not in {"__pycache__/", "*.py[cod]"} for x in added):
                raise SystemExit("A0 .gitignore additions are not allowlisted")
            continue
        if len(removed) != len(added) or not removed:
            raise SystemExit(f"A0 requires one-for-one safe replacements in {path}")
        for old, new in zip(removed, added):
            if not safe_replacement(old, new):
                raise SystemExit(f"unsafe A0 replacement in {path}: {old!r} -> {new!r}")
    if total_lines > 80:
        raise SystemExit("A0 repair diff is too large")

    expected: set[str] = set()
    for path in changed:
        expected |= EXPECTED_WORKFLOWS_BY_PATH.get(path, set())
    return {"changed_paths": sorted(changed), "changed_lines": total_lines, "expected_workflows": sorted(expected)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("base")
    parser.add_argument("head", nargs="?")
    parser.add_argument("--worktree", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.worktree and args.head is not None:
        raise SystemExit("--worktree does not take HEAD")
    if not args.worktree and args.head is None:
        raise SystemExit("HEAD is required unless --worktree is used")
    result = validate(args.base, args.head, args.worktree)
    payload = json.dumps(result, sort_keys=True)
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
