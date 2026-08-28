#!/usr/bin/env python3
"""Validate and execute bounded Reviewer challenges for PolaCore #90.

Generated challenge code is untrusted evidence. This module is a deterministic,
offline Lab contract: it validates a deliberately small Python unittest subset,
runs the exact same challenge bytes against candidate and hidden-repair source,
and reports only causal execution evidence. It has no GitHub/model/network client
and grants no publication or merge authority.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any

SCHEMA = "polacore.reviewer-executable-challenge/v1"
RESULT_SCHEMA = "polacore.reviewer-executable-result/v1"
MAX_CODE_BYTES = 12_000
MAX_RATIONALE = 600
MAX_AST_NODES = 1_500
MAX_OUTPUT_BYTES = 1_000_000
DEFAULT_TIMEOUT_SECONDS = 4.0

ALLOWED_IMPORT_ROOTS = {
    "candidate",
    "contextlib",
    "datetime",
    "io",
    "json",
    "types",
    "unittest",
}
FORBIDDEN_CALL_NAMES = {
    "__import__",
    "breakpoint",
    "compile",
    "delattr",
    "dir",
    "eval",
    "exec",
    "getattr",
    "globals",
    "help",
    "input",
    "locals",
    "open",
    "setattr",
    "vars",
}
FORBIDDEN_NODES = (
    ast.AsyncFunctionDef,
    ast.Await,
    ast.Global,
    ast.Nonlocal,
    ast.Yield,
    ast.YieldFrom,
)


class UnsafeChallenge(ValueError):
    """Raised when generated test code exceeds the trusted execution contract."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _simple_testcase_base(node: ast.expr) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "TestCase"
        and isinstance(node.value, ast.Name)
        and node.value.id == "unittest"
    )


def _validate_top_level(tree: ast.Module) -> None:
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef)):
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            continue
        if isinstance(node, ast.Assign):
            if not isinstance(node.value, (ast.Constant, ast.List, ast.Tuple, ast.Dict, ast.Set)):
                raise UnsafeChallenge("top-level assignments must be literal data only")
            continue
        raise UnsafeChallenge(f"top-level executable statement is forbidden: {type(node).__name__}")


def validate_code(code: str) -> ast.Module:
    raw = code.encode("utf-8")
    if not raw or len(raw) > MAX_CODE_BYTES or b"\x00" in raw:
        raise UnsafeChallenge("challenge code size/content is outside contract")
    try:
        tree = ast.parse(code, filename="challenge_test.py", mode="exec")
    except SyntaxError as exc:
        raise UnsafeChallenge("challenge code is not valid Python") from exc
    nodes = list(ast.walk(tree))
    if len(nodes) > MAX_AST_NODES:
        raise UnsafeChallenge("challenge AST is too large")
    _validate_top_level(tree)

    imported_candidate = False
    imported_unittest = False
    test_methods = 0
    for node in nodes:
        if isinstance(node, FORBIDDEN_NODES):
            raise UnsafeChallenge(f"forbidden syntax: {type(node).__name__}")
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root not in ALLOWED_IMPORT_ROOTS:
                    raise UnsafeChallenge(f"forbidden import: {alias.name}")
                if root in {"candidate", "unittest"} and alias.asname is not None:
                    raise UnsafeChallenge(f"aliasing {root} is forbidden")
                imported_candidate = imported_candidate or root == "candidate"
                imported_unittest = imported_unittest or root == "unittest"
        elif isinstance(node, ast.ImportFrom):
            if node.level != 0 or not node.module:
                raise UnsafeChallenge("relative/empty imports are forbidden")
            root = node.module.split(".", 1)[0]
            if root == "candidate":
                raise UnsafeChallenge("from candidate imports are forbidden")
            if root not in ALLOWED_IMPORT_ROOTS:
                raise UnsafeChallenge(f"forbidden import: {node.module}")
            imported_unittest = imported_unittest or root == "unittest"
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__"):
                raise UnsafeChallenge("dunder attribute access is forbidden")
        elif isinstance(node, ast.Name):
            if node.id.startswith("__") and node.id != "__name__":
                raise UnsafeChallenge("dunder name access is forbidden")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALL_NAMES:
                raise UnsafeChallenge(f"forbidden call: {node.func.id}")
        elif isinstance(node, ast.FunctionDef):
            if node.decorator_list:
                raise UnsafeChallenge("decorators are forbidden")
            if node.name.startswith("__"):
                raise UnsafeChallenge("dunder functions are forbidden")
        elif isinstance(node, ast.ClassDef):
            if node.decorator_list or node.keywords:
                raise UnsafeChallenge("class decorators/metaclasses are forbidden")
            if len(node.bases) != 1 or not _simple_testcase_base(node.bases[0]):
                raise UnsafeChallenge("only unittest.TestCase classes are allowed")
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name.startswith("test_"):
                    test_methods += 1

    if not imported_candidate:
        raise UnsafeChallenge("challenge must import candidate")
    if not imported_unittest:
        raise UnsafeChallenge("challenge must import unittest")
    if test_methods < 1:
        raise UnsafeChallenge("challenge must define at least one unittest test method")
    return tree


def validate_challenge(value: object) -> dict[str, str]:
    required = {"schema", "name", "rationale", "code"}
    if not isinstance(value, dict) or set(value) != required:
        raise UnsafeChallenge("challenge object has invalid keys")
    if value.get("schema") != SCHEMA:
        raise UnsafeChallenge("challenge schema mismatch")
    name = value.get("name")
    rationale = value.get("rationale")
    code = value.get("code")
    if not isinstance(name, str) or not re.fullmatch(r"challenge_[a-z0-9_]{3,80}", name):
        raise UnsafeChallenge("challenge name is invalid")
    if not isinstance(rationale, str) or not 20 <= len(rationale) <= MAX_RATIONALE:
        raise UnsafeChallenge("challenge rationale length is outside contract")
    if not isinstance(code, str):
        raise UnsafeChallenge("challenge code must be a string")
    validate_code(code)
    return {"schema": SCHEMA, "name": name, "rationale": rationale, "code": code}


def challenge_digest(challenge: dict[str, str]) -> str:
    return _sha256(challenge["code"].encode("utf-8"))


_LAUNCHER = r'''
import builtins
import os
import resource
import socket
import subprocess
import sys
import unittest

root = os.path.realpath(sys.argv[1])

def blocked(*args, **kwargs):
    raise RuntimeError("POLACORE_SANDBOX_BLOCKED")

# Keep the socket class import-compatible for urllib/http/ssl, but block every
# operation capable of establishing or accepting network communication.
for name in ("connect", "connect_ex", "bind", "listen", "accept", "sendto", "recvfrom"):
    if hasattr(socket.socket, name):
        setattr(socket.socket, name, blocked)
for name in ("create_connection", "create_server", "socketpair"):
    if hasattr(socket, name):
        setattr(socket, name, blocked)

# Generated tests cannot import process modules; candidate code may, so block
# process creation/exec again at runtime.
for name in ("Popen", "run", "call", "check_call", "check_output"):
    if hasattr(subprocess, name):
        setattr(subprocess, name, blocked)
for name in (
    "system", "popen", "fork", "forkpty", "spawnl", "spawnle", "spawnlp",
    "spawnlpe", "spawnv", "spawnve", "spawnvp", "spawnvpe",
    "execl", "execle", "execlp", "execlpe", "execv", "execve", "execvp", "execvpe",
):
    if hasattr(os, name):
        setattr(os, name, blocked)

original_open = builtins.open
read_roots = [root]
for item in sys.path:
    if item:
        try:
            read_roots.append(os.path.realpath(item))
        except (OSError, TypeError):
            pass

def within(path, base):
    return path == base or path.startswith(base + os.sep)

def require_read_path(file):
    path = os.path.realpath(os.fspath(file))
    if not any(within(path, base) for base in read_roots):
        raise RuntimeError("POLACORE_FS_READ_BLOCKED")
    return path

def require_write_path(file):
    path = os.path.realpath(os.fspath(file))
    if not within(path, root):
        raise RuntimeError("POLACORE_FS_WRITE_BLOCKED")
    return path

def guarded_open(file, mode="r", *args, **kwargs):
    writing = any(flag in mode for flag in ("w", "a", "x", "+"))
    if writing:
        require_write_path(file)
    else:
        require_read_path(file)
    return original_open(file, mode, *args, **kwargs)

builtins.open = guarded_open

original_listdir = os.listdir
original_scandir = os.scandir

def guarded_listdir(path="."):
    require_read_path(path)
    return original_listdir(path)

def guarded_scandir(path="."):
    require_read_path(path)
    return original_scandir(path)

os.listdir = guarded_listdir
os.scandir = guarded_scandir

# Mutating filesystem operations are allowed only inside the disposable root.
def guard_one_path(name):
    original = getattr(os, name, None)
    if original is None:
        return
    def guarded(path, *args, **kwargs):
        require_write_path(path)
        return original(path, *args, **kwargs)
    setattr(os, name, guarded)

for name in ("remove", "unlink", "rmdir", "mkdir", "chmod", "truncate", "mkfifo", "mknod"):
    guard_one_path(name)

for name in ("rename", "replace", "link", "symlink"):
    original = getattr(os, name, None)
    if original is None:
        continue
    def make_guarded_pair(function):
        def guarded(src, dst, *args, **kwargs):
            require_write_path(src)
            require_write_path(dst)
            return function(src, dst, *args, **kwargs)
        return guarded
    setattr(os, name, make_guarded_pair(original))

original_chdir = os.chdir

def guarded_chdir(path):
    require_write_path(path)
    return original_chdir(path)

os.chdir = guarded_chdir

for kind, value in (
    (resource.RLIMIT_CORE, (0, 0)),
    (resource.RLIMIT_FSIZE, (1000000, 1000000)),
    (resource.RLIMIT_NOFILE, (64, 64)),
    (resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024)),
):
    try:
        resource.setrlimit(kind, value)
    except (ValueError, OSError):
        pass
try:
    resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
except (ValueError, OSError):
    pass

sys.path.insert(0, root)
suite = unittest.defaultTestLoader.discover(root, pattern="challenge_test.py")
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
'''


def _bounded_digest(data: bytes) -> dict[str, Any]:
    return {"bytes": len(data), "sha256": _sha256(data)}


def _read_output(path: Path) -> tuple[dict[str, Any], bool]:
    data = path.read_bytes()
    overflow = len(data) >= MAX_OUTPUT_BYTES
    return _bounded_digest(data), overflow


def _run_source(
    source: bytes,
    challenge: dict[str, str],
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="polacore-challenge-") as tmp:
        root = Path(tmp)
        (root / "candidate.py").write_bytes(source)
        (root / "challenge_test.py").write_text(challenge["code"], encoding="utf-8")
        stdout_path = root / "stdout.bin"
        stderr_path = root / "stderr.bin"
        env = {
            "HOME": str(root),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PATH": os.path.dirname(sys.executable),
            "TZ": "UTC",
        }
        status = "RUNNER_ERROR"
        returncode: int | None = None
        error: str | None = None
        try:
            with stdout_path.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
                proc = subprocess.run(
                    [sys.executable, "-I", "-c", _LAUNCHER, str(root)],
                    cwd=root,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout_handle,
                    stderr=stderr_handle,
                    timeout=timeout_seconds,
                    check=False,
                )
            returncode = proc.returncode
            status = "PASS" if proc.returncode == 0 else "FAIL"
        except subprocess.TimeoutExpired:
            status = "TIMEOUT"
        except OSError as exc:
            status = "RUNNER_ERROR"
            error = type(exc).__name__

        stdout, stdout_overflow = _read_output(stdout_path)
        stderr, stderr_overflow = _read_output(stderr_path)
        if stdout_overflow or stderr_overflow:
            status = "OUTPUT_LIMIT"
        result: dict[str, Any] = {
            "status": status,
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
        }
        if error is not None:
            result["error"] = error
        return result


def run_pair(
    challenge_value: object,
    candidate_source: bytes,
    repair_source: bytes,
    *,
    candidate_sha: str = "UNBOUND_CANDIDATE",
    repair_sha: str = "UNBOUND_REPAIR",
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    challenge = validate_challenge(challenge_value)
    candidate = _run_source(candidate_source, challenge, timeout_seconds=timeout_seconds)
    repair = _run_source(repair_source, challenge, timeout_seconds=timeout_seconds)
    uncertain = {"TIMEOUT", "RUNNER_ERROR", "OUTPUT_LIMIT"}
    if candidate["status"] in uncertain or repair["status"] in uncertain:
        outcome = "UNPROVEN"
    elif candidate["status"] == "FAIL" and repair["status"] == "PASS":
        outcome = "DETECTED"
    else:
        outcome = "NO_CAUSAL_DISTINCTION"
    return {
        "schema": RESULT_SCHEMA,
        "mode": "PAIR",
        "authority": "EXECUTABLE_EVIDENCE_ONLY",
        "challenge_name": challenge["name"],
        "challenge_sha256": challenge_digest(challenge),
        "candidate_sha": candidate_sha,
        "candidate_source_sha256": _sha256(candidate_source),
        "repair_sha": repair_sha,
        "repair_source_sha256": _sha256(repair_source),
        "candidate": candidate,
        "repair": repair,
        "outcome": outcome,
    }


def run_control(
    challenge_value: object,
    source: bytes,
    *,
    candidate_sha: str = "UNBOUND_CONTROL",
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    challenge = validate_challenge(challenge_value)
    result = _run_source(source, challenge, timeout_seconds=timeout_seconds)
    if result["status"] in {"TIMEOUT", "RUNNER_ERROR", "OUTPUT_LIMIT"}:
        outcome = "UNPROVEN"
    elif result["status"] == "PASS":
        outcome = "CLEAN_CONTROL"
    else:
        outcome = "FALSE_POSITIVE"
    return {
        "schema": RESULT_SCHEMA,
        "mode": "CONTROL",
        "authority": "EXECUTABLE_EVIDENCE_ONLY",
        "challenge_name": challenge["name"],
        "challenge_sha256": challenge_digest(challenge),
        "candidate_sha": candidate_sha,
        "candidate_source_sha256": _sha256(source),
        "candidate": result,
        "outcome": outcome,
    }


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate")
    validate.add_argument("--challenge", required=True, type=Path)

    pair = sub.add_parser("run-pair")
    pair.add_argument("--challenge", required=True, type=Path)
    pair.add_argument("--candidate", required=True, type=Path)
    pair.add_argument("--repair", required=True, type=Path)
    pair.add_argument("--candidate-sha", required=True)
    pair.add_argument("--repair-sha", required=True)
    pair.add_argument("--out", required=True, type=Path)

    control = sub.add_parser("run-control")
    control.add_argument("--challenge", required=True, type=Path)
    control.add_argument("--candidate", required=True, type=Path)
    control.add_argument("--candidate-sha", required=True)
    control.add_argument("--out", required=True, type=Path)

    args = parser.parse_args()
    challenge_value = _load_json(args.challenge)
    if args.command == "validate":
        challenge = validate_challenge(challenge_value)
        print(json.dumps({"schema": SCHEMA, "name": challenge["name"], "challenge_sha256": challenge_digest(challenge)}, sort_keys=True))
        return
    if args.command == "run-pair":
        result = run_pair(
            challenge_value,
            args.candidate.read_bytes(),
            args.repair.read_bytes(),
            candidate_sha=args.candidate_sha,
            repair_sha=args.repair_sha,
        )
    else:
        result = run_control(
            challenge_value,
            args.candidate.read_bytes(),
            candidate_sha=args.candidate_sha,
        )
    _write(args.out, result)


if __name__ == "__main__":
    main()
