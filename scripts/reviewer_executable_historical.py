#!/usr/bin/env python3
"""Hardened historical executable-challenge runner for PolaCore #90.

This layer deliberately leaves the #91 sandbox root unchanged. It re-validates
an already bounded challenge for the historical Merge Provider corpus, blocks
access to candidate-exported capability modules except for three narrow test
hooks, loads only fixed byte-identical local support modules, and executes in a
fresh no-secret/no-network/no-publication child process.
"""
from __future__ import annotations

import ast
import hashlib
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
from typing import Any

try:
    import reviewer_executable_challenge as base
except ModuleNotFoundError:  # pragma: no cover - package import in unit tests
    from scripts import reviewer_executable_challenge as base


SCHEMA = "polacore.reviewer-executable-historical/v1"
MAX_SUPPORT_BYTES = 200_000
SUPPORT_NAMES = frozenset({"merge_governor.py", "merge_provider_capability.py"})
EXACT_IMPORTS = frozenset({"candidate", "contextlib", "datetime", "json", "types", "unittest"})
DANGEROUS_CANDIDATE_ROOTS = frozenset(
    {"sys", "os", "urllib", "pathlib", "subprocess", "socket", "builtins", "importlib", "io"}
)
ALLOWED_DANGEROUS_PREFIXES = (
    ("candidate", "sys", "argv"),
    ("candidate", "os", "environ"),
    ("candidate", "urllib", "request", "build_opener"),
)
MAX_OUTPUT_BYTES = base.MAX_OUTPUT_BYTES
DEFAULT_TIMEOUT_SECONDS = base.DEFAULT_TIMEOUT_SECONDS


class HistoricalChallengeError(base.UnsafeChallenge):
    """Historical runner contract violation."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _attribute_chain(node: ast.AST) -> tuple[str, ...] | None:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        return None
    parts.append(current.id)
    return tuple(reversed(parts))


def _is_prefix(value: tuple[str, ...], prefix: tuple[str, ...]) -> bool:
    return len(value) >= len(prefix) and value[: len(prefix)] == prefix


def validate_historical_challenge(value: object) -> dict[str, str]:
    challenge = base.validate_challenge(value)
    tree = ast.parse(challenge["code"], filename="challenge_test.py", mode="exec")
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name not in EXACT_IMPORTS or alias.asname is not None:
                    raise HistoricalChallengeError(f"historical import is forbidden: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            raise HistoricalChallengeError("from-import syntax is forbidden in historical challenges")
        elif isinstance(node, ast.Attribute):
            parent = parents.get(node)
            if isinstance(parent, ast.Attribute) and parent.value is node:
                continue
            chain = _attribute_chain(node)
            if not chain or len(chain) < 2 or chain[0] != "candidate":
                continue
            first = chain[1]
            if first not in DANGEROUS_CANDIDATE_ROOTS:
                continue
            if not any(_is_prefix(chain, prefix) for prefix in ALLOWED_DANGEROUS_PREFIXES):
                raise HistoricalChallengeError(
                    "candidate-exported capability access is forbidden: " + ".".join(chain)
                )
    return challenge


def validate_support_files(value: object) -> dict[str, bytes]:
    if not isinstance(value, dict) or set(value) != SUPPORT_NAMES:
        raise HistoricalChallengeError("historical support set must contain exactly the fixed modules")
    normalized: dict[str, bytes] = {}
    for name in sorted(SUPPORT_NAMES):
        data = value.get(name)
        if not isinstance(data, bytes) or not data or len(data) > MAX_SUPPORT_BYTES or b"\x00" in data:
            raise HistoricalChallengeError(f"invalid historical support bytes: {name}")
        try:
            compile(data, name, "exec")
        except (SyntaxError, ValueError) as exc:
            raise HistoricalChallengeError(f"historical support is not valid Python: {name}") from exc
        normalized[name] = data
    return normalized


def support_digests(support: dict[str, bytes]) -> dict[str, str]:
    return {name: _sha256(data) for name, data in sorted(support.items())}


_LAUNCHER = r'''
import builtins
import io
import os
import resource
import socket
import subprocess
import sys
import unittest

root = os.path.realpath(sys.argv[1])

def blocked(*args, **kwargs):
    raise RuntimeError("POLACORE_SANDBOX_BLOCKED")

for name in ("connect", "connect_ex", "bind", "listen", "accept", "sendto", "recvfrom"):
    if hasattr(socket.socket, name):
        setattr(socket.socket, name, blocked)
for name in ("create_connection", "create_server", "socketpair"):
    if hasattr(socket, name):
        setattr(socket, name, blocked)
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
original_io_open = io.open
original_os_open = os.open
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

def guarded_io_open(file, mode="r", *args, **kwargs):
    writing = any(flag in mode for flag in ("w", "a", "x", "+"))
    if writing:
        require_write_path(file)
    else:
        require_read_path(file)
    return original_io_open(file, mode, *args, **kwargs)

def guarded_os_open(file, flags, *args, **kwargs):
    write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
    if flags & write_flags:
        require_write_path(file)
    else:
        require_read_path(file)
    return original_os_open(file, flags, *args, **kwargs)

builtins.open = guarded_open
io.open = guarded_io_open
os.open = guarded_os_open

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
    return _bounded_digest(data), len(data) >= MAX_OUTPUT_BYTES


def _run_source(
    source: bytes,
    challenge: dict[str, str],
    support: dict[str, bytes],
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="polacore-historical-challenge-") as tmp:
        root = Path(tmp)
        (root / "candidate.py").write_bytes(source)
        (root / "challenge_test.py").write_text(challenge["code"], encoding="utf-8")
        for name, data in support.items():
            (root / name).write_bytes(data)
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
    support_value: object,
    *,
    candidate_sha: str,
    repair_sha: str,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    challenge = validate_historical_challenge(challenge_value)
    support = validate_support_files(support_value)
    candidate = _run_source(candidate_source, challenge, support, timeout_seconds=timeout_seconds)
    repair = _run_source(repair_source, challenge, support, timeout_seconds=timeout_seconds)
    uncertain = {"TIMEOUT", "RUNNER_ERROR", "OUTPUT_LIMIT"}
    if candidate["status"] in uncertain or repair["status"] in uncertain:
        outcome = "UNPROVEN"
    elif candidate["status"] == "FAIL" and repair["status"] == "PASS":
        outcome = "DETECTED"
    else:
        outcome = "NO_CAUSAL_DISTINCTION"
    return {
        "schema": SCHEMA,
        "mode": "PAIR",
        "authority": "EXECUTABLE_EVIDENCE_ONLY",
        "challenge_name": challenge["name"],
        "challenge_sha256": base.challenge_digest(challenge),
        "candidate_sha": candidate_sha,
        "candidate_source_sha256": _sha256(candidate_source),
        "repair_sha": repair_sha,
        "repair_source_sha256": _sha256(repair_source),
        "support_sha256": support_digests(support),
        "candidate": candidate,
        "repair": repair,
        "outcome": outcome,
    }


def run_control(
    challenge_value: object,
    source: bytes,
    support_value: object,
    *,
    candidate_sha: str,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    challenge = validate_historical_challenge(challenge_value)
    support = validate_support_files(support_value)
    candidate = _run_source(source, challenge, support, timeout_seconds=timeout_seconds)
    if candidate["status"] in {"TIMEOUT", "RUNNER_ERROR", "OUTPUT_LIMIT"}:
        outcome = "UNPROVEN"
    elif candidate["status"] == "PASS":
        outcome = "CLEAN_CONTROL"
    else:
        outcome = "FALSE_POSITIVE"
    return {
        "schema": SCHEMA,
        "mode": "CONTROL",
        "authority": "EXECUTABLE_EVIDENCE_ONLY",
        "challenge_name": challenge["name"],
        "challenge_sha256": base.challenge_digest(challenge),
        "candidate_sha": candidate_sha,
        "candidate_source_sha256": _sha256(source),
        "support_sha256": support_digests(support),
        "candidate": candidate,
        "outcome": outcome,
    }
