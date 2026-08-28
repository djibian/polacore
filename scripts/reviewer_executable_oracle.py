#!/usr/bin/env python3
"""Hidden causal oracle for PolaCore executable challenge experiment #90.

This module is used only by the no-secret execution job. It knows candidate to
repair pairs, verifies local support modules are byte-identical across each pair,
and delegates generated code execution to the trusted historical sandbox. It has
no model/provider client and no GitHub publication authority.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
from typing import Any, Callable, NamedTuple

try:
    import reviewer_executable_historical as historical
except ModuleNotFoundError:  # pragma: no cover
    from scripts import reviewer_executable_historical as historical


SCHEMA = "polacore.reviewer-executable-oracle/v1"
SYNTHESIS_SCHEMA = "polacore.reviewer-executable-synthesis/v1"
MODEL = "qwen3-coder-30b-A3b-instruct"
CANDIDATE_PATH = "scripts/merge_provider_live_collect.py"
SUPPORT_PATHS = {
    "merge_governor.py": "scripts/merge_governor.py",
    "merge_provider_capability.py": "scripts/merge_provider_capability.py",
}


class CaseSpec(NamedTuple):
    candidate_sha: str
    repair_sha: str | None


CASES: dict[str, CaseSpec] = {
    "alpha": CaseSpec("86d66be36f4ea10a0a83b7fac1639951f1df72c1", "c790315c92663aa7b15b9a626ae5d9fc07d3e378"),
    "beta": CaseSpec("884ef3c07c9c19f13d11bbbe1dbc3211f748b586", "9a653e50d1bec813ae738106cd65e0b2cde29dcb"),
    "gamma": CaseSpec("4236ed98f937b1e1fd9dcaefddffe711f0673a8f", "a821bcae50dadfd3f4d758056585162065d6ea30"),
    "delta": CaseSpec("7fce52d8b8fd7e3a26e79d9609847f63a8fc38ce", None),
}
VALID_SYNTHESIS_STATUSES = {"VALID", "PROVIDER_FAILURE", "MODEL_OUTPUT_INVALID"}
Fetch = Callable[[str, str], bytes]


def required_shas() -> list[str]:
    values: list[str] = []
    for spec in CASES.values():
        values.append(spec.candidate_sha)
        if spec.repair_sha is not None:
            values.append(spec.repair_sha)
    return list(dict.fromkeys(values))


def git_show(sha: str, path: str) -> bytes:
    proc = subprocess.run(
        ["git", "show", f"{sha}:{path}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0 or not proc.stdout or b"\x00" in proc.stdout:
        raise ValueError(f"oracle source unavailable: {sha}:{path}")
    return proc.stdout


def support_at(sha: str, fetch: Fetch = git_show) -> dict[str, bytes]:
    return {local: fetch(sha, repo_path) for local, repo_path in SUPPORT_PATHS.items()}


def _validate_synthesis(value: object) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"schema", "model", "cases"}:
        raise ValueError("synthesis bundle has invalid top-level shape")
    if value.get("schema") != SYNTHESIS_SCHEMA or value.get("model") != MODEL:
        raise ValueError("synthesis bundle identity mismatch")
    cases = value.get("cases")
    if not isinstance(cases, dict) or set(cases) != set(CASES):
        raise ValueError("synthesis bundle must contain the exact neutral case set")
    normalized: dict[str, Any] = {}
    for token in sorted(CASES):
        record = cases[token]
        if not isinstance(record, dict):
            raise ValueError(f"synthesis case {token} must be an object")
        status = record.get("status")
        if status not in VALID_SYNTHESIS_STATUSES:
            raise ValueError(f"synthesis case {token} status is invalid")
        expected_keys = {"status", "challenge"} if status == "VALID" else {"status", "reason"}
        if set(record) != expected_keys:
            raise ValueError(f"synthesis case {token} keys do not match status")
        if status == "VALID":
            normalized[token] = {
                "status": status,
                "challenge": historical.validate_historical_challenge(record["challenge"]),
            }
        else:
            reason = record.get("reason")
            if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
                raise ValueError(f"synthesis case {token} reason is invalid")
            normalized[token] = {"status": status, "reason": " ".join(reason.split())}
    return {"schema": SYNTHESIS_SCHEMA, "model": MODEL, "cases": normalized}


def evaluate_case(token: str, record: dict[str, Any], fetch: Fetch = git_show) -> dict[str, Any]:
    if token not in CASES:
        raise ValueError("unknown oracle case token")
    spec = CASES[token]
    if record["status"] != "VALID":
        return {
            "case_token": token,
            "synthesis_status": record["status"],
            "outcome": "UNPROVEN",
            "reason": record["reason"],
            "authority": "EXECUTABLE_EVIDENCE_ONLY",
        }
    challenge = record["challenge"]
    candidate_source = fetch(spec.candidate_sha, CANDIDATE_PATH)
    candidate_support = support_at(spec.candidate_sha, fetch)
    if spec.repair_sha is None:
        result = historical.run_control(
            challenge,
            candidate_source,
            candidate_support,
            candidate_sha=spec.candidate_sha,
        )
    else:
        repair_source = fetch(spec.repair_sha, CANDIDATE_PATH)
        repair_support = support_at(spec.repair_sha, fetch)
        if historical.support_digests(candidate_support) != historical.support_digests(repair_support):
            return {
                "case_token": token,
                "synthesis_status": "VALID",
                "outcome": "UNPROVEN",
                "reason": "candidate/repair support modules are not byte-identical",
                "authority": "EXECUTABLE_EVIDENCE_ONLY",
            }
        result = historical.run_pair(
            challenge,
            candidate_source,
            repair_source,
            candidate_support,
            candidate_sha=spec.candidate_sha,
            repair_sha=spec.repair_sha,
        )
    return {
        "case_token": token,
        "synthesis_status": "VALID",
        "authority": "EXECUTABLE_EVIDENCE_ONLY",
        "execution": result,
        "outcome": result["outcome"],
    }


def evaluate(value: object, fetch: Fetch = git_show) -> dict[str, Any]:
    synthesis = _validate_synthesis(value)
    cases = {token: evaluate_case(token, synthesis["cases"][token], fetch) for token in sorted(CASES)}
    detected = sum(cases[token]["outcome"] == "DETECTED" for token in ("alpha", "beta", "gamma"))
    control = cases["delta"]["outcome"]
    qualified = detected == 3 and control == "CLEAN_CONTROL" and all(
        row["synthesis_status"] == "VALID" for row in cases.values()
    )
    return {
        "schema": SCHEMA,
        "architecture": "blind_model_challenge_then_hidden_causal_execution",
        "model": MODEL,
        "historical_detected": detected,
        "historical_total": 3,
        "negative_control": control,
        "cases": cases,
        "result": "QUALIFIED_FOR_REPEAT" if qualified else "NOT_QUALIFIED",
        "authority": "EXECUTABLE_EVIDENCE_ONLY",
        "note": "This experiment does not amend #48 or authorize merge eligibility.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("required-shas")
    run = sub.add_parser("evaluate")
    run.add_argument("--synthesis", required=True, type=Path)
    run.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "required-shas":
        print(" ".join(required_shas()))
        return
    value = json.loads(args.synthesis.read_text(encoding="utf-8"))
    result = evaluate(value)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
