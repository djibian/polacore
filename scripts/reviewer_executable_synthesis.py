#!/usr/bin/env python3
"""Assemble neutral #90 challenge-synthesis records without hidden oracle data."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    import reviewer_executable_historical as historical
except ModuleNotFoundError:  # pragma: no cover
    from scripts import reviewer_executable_historical as historical


SCHEMA = "polacore.reviewer-executable-synthesis/v1"
MODEL = "qwen3-coder-30b-A3b-instruct"
CASES = frozenset({"alpha", "beta", "gamma", "delta"})
STATUSES = frozenset({"VALID", "PROVIDER_FAILURE", "MODEL_OUTPUT_INVALID"})


def record(case_token: str, status: str, *, challenge: object | None = None, reason: str = "") -> dict[str, Any]:
    if case_token not in CASES or status not in STATUSES:
        raise ValueError("invalid neutral synthesis identity/status")
    if status == "VALID":
        return {
            "case_token": case_token,
            "status": status,
            "challenge": historical.validate_historical_challenge(challenge),
        }
    normalized = " ".join(reason.split())[:500]
    if not normalized:
        raise ValueError("failed synthesis record requires a bounded reason")
    return {"case_token": case_token, "status": status, "reason": normalized}


def summarize(values: list[object]) -> dict[str, Any]:
    by_case: dict[str, dict[str, Any]] = {}
    for value in values:
        if not isinstance(value, dict):
            raise ValueError("synthesis record must be an object")
        token = value.get("case_token")
        status = value.get("status")
        if token in by_case:
            raise ValueError("duplicate synthesis case")
        if status == "VALID":
            row = record(str(token), str(status), challenge=value.get("challenge"))
            by_case[str(token)] = {"status": row["status"], "challenge": row["challenge"]}
        else:
            row = record(str(token), str(status), reason=str(value.get("reason", "")))
            by_case[str(token)] = {"status": row["status"], "reason": row["reason"]}
    if set(by_case) != CASES:
        raise ValueError("synthesis records must cover the exact neutral case set")
    return {"schema": SCHEMA, "model": MODEL, "cases": {token: by_case[token] for token in sorted(CASES)}}


def _read(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    r = sub.add_parser("record")
    r.add_argument("--case", required=True, choices=sorted(CASES))
    r.add_argument("--status", required=True, choices=sorted(STATUSES))
    r.add_argument("--challenge", type=Path)
    r.add_argument("--reason", default="")
    r.add_argument("--out", required=True, type=Path)
    s = sub.add_parser("summarize")
    s.add_argument("--inputs", required=True, nargs="+", type=Path)
    s.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "record":
        value = record(
            args.case,
            args.status,
            challenge=_read(args.challenge) if args.challenge else None,
            reason=args.reason,
        )
        _write(args.out, value)
    else:
        _write(args.out, summarize([_read(path) for path in args.inputs]))


if __name__ == "__main__":
    main()
