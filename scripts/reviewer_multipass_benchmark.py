#!/usr/bin/env python3
"""Build and summarize bounded multi-pass Reviewer evidence for PolaCore #65.

This helper is deterministic and offline. Hidden defect signatures remain solely in
reviewer_provider_eval.py; this module only combines already-validated pass records,
per-pass scorer statuses, and the fail-closed aggregate produced by
reviewer_multipass_aggregate.py.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

if __package__:
    from . import reviewer_multipass_aggregate as multipass
else:
    import reviewer_multipass_aggregate as multipass

SCHEMA = "polacore.reviewer-multipass-benchmark/v1"
MODEL = "mistral-small-3-2-24b-instruct-2506"
HISTORICAL_CASES = ("H1", "H2", "H3")
NEGATIVE_CONTROL = "H4"
ALL_CASES = HISTORICAL_CASES + (NEGATIVE_CONTROL,)


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def valid_record(case: str, pass_id: str, decision_path: Path) -> dict[str, Any]:
    if case not in ALL_CASES:
        raise SystemExit(f"unknown case: {case}")
    if pass_id not in multipass.REQUIRED_PASSES:
        raise SystemExit(f"unknown pass: {pass_id}")
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    if not isinstance(decision, dict):
        raise SystemExit("decision must be an object")
    record = {
        "schema": multipass.PASS_SCHEMA,
        "case": case,
        "pass_id": pass_id,
        "status": "VALID",
        "decision": {
            "verdict": decision.get("verdict"),
            "confidence": decision.get("confidence"),
            "rationale": decision.get("rationale"),
        },
    }
    normalized, error = multipass._normalize_record(record)
    if normalized is None:
        raise SystemExit(f"validated decision cannot form a pass record: {error}")
    return normalized


def failure_record(case: str, pass_id: str, status: str, reason: str) -> dict[str, Any]:
    if case not in ALL_CASES:
        raise SystemExit(f"unknown case: {case}")
    if pass_id not in multipass.REQUIRED_PASSES:
        raise SystemExit(f"unknown pass: {pass_id}")
    if status not in {"PROVIDER_FAILURE", "MODEL_OUTPUT_INVALID"}:
        raise SystemExit("failure status is invalid")
    record = {
        "schema": multipass.PASS_SCHEMA,
        "case": case,
        "pass_id": pass_id,
        "status": status,
        "reason": " ".join(reason.split())[:500],
    }
    normalized, error = multipass._normalize_record(record)
    if normalized is None:
        raise SystemExit(f"failure record is invalid: {error}")
    return normalized


def _load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _case_summary(root: Path, case: str) -> dict[str, Any]:
    case_dir = root / case
    aggregate_path = case_dir / "aggregate.json"
    errors: list[str] = []
    if not aggregate_path.exists():
        return {
            "case": case,
            "aggregate_status": "MISSING",
            "aggregate_disposition": "BLOCKING",
            "detected_passes": [],
            "clean_control_passes": [],
            "score_statuses": {},
            "errors": ["aggregate result is missing"],
        }

    aggregate = _load(aggregate_path)
    if not isinstance(aggregate, dict):
        errors.append("aggregate result must be an object")
        aggregate = {}
    if aggregate.get("schema") != multipass.SCHEMA:
        errors.append("aggregate schema is invalid")
    if aggregate.get("case") != case:
        errors.append("aggregate case binding is invalid")
    if aggregate.get("authority") != "INFERENCE_ONLY":
        errors.append("aggregate authority boundary is invalid")
    if aggregate.get("required_passes") != list(multipass.REQUIRED_PASSES):
        errors.append("aggregate required-pass set is invalid")

    detected: list[str] = []
    clean: list[str] = []
    score_statuses: dict[str, str] = {}
    for pass_id in multipass.REQUIRED_PASSES:
        score_path = case_dir / f"{pass_id}.score.json"
        if not score_path.exists():
            score_statuses[pass_id] = "MISSING"
            errors.append(f"score missing for {pass_id}")
            continue
        score = _load(score_path)
        if not isinstance(score, dict):
            score_statuses[pass_id] = "INVALID"
            errors.append(f"score invalid for {pass_id}")
            continue
        if score.get("case") != case:
            errors.append(f"score case mismatch for {pass_id}")
        if score.get("model") != MODEL:
            errors.append(f"score model mismatch for {pass_id}")
        status = str(score.get("status", "MISSING"))
        score_statuses[pass_id] = status
        if status == "DETECTED":
            detected.append(pass_id)
        if status == "CLEAN_CONTROL":
            clean.append(pass_id)

    return {
        "case": case,
        "aggregate_status": aggregate.get("status", "MISSING"),
        "aggregate_disposition": aggregate.get("disposition", "BLOCKING"),
        "aggregate_verdict": aggregate.get("aggregate_verdict", "BLOCKED"),
        "aggregate_digest": aggregate.get("aggregate_digest"),
        "detected_passes": detected,
        "clean_control_passes": clean,
        "score_statuses": score_statuses,
        "errors": errors,
    }


def summarize(root: Path) -> dict[str, Any]:
    cases = {case: _case_summary(root, case) for case in ALL_CASES}
    historical_ok = {
        case: (
            cases[case]["aggregate_status"] == "COMPLETE"
            and bool(cases[case]["detected_passes"])
            and not cases[case]["errors"]
        )
        for case in HISTORICAL_CASES
    }
    h4 = cases[NEGATIVE_CONTROL]
    negative_control_ok = (
        h4["aggregate_status"] == "COMPLETE"
        and h4["aggregate_disposition"] == "NON_BLOCKING"
        and h4["clean_control_passes"] == list(multipass.REQUIRED_PASSES)
        and not h4["errors"]
    )
    qualified = all(historical_ok.values()) and negative_control_ok
    return {
        "schema": SCHEMA,
        "provider": "albert",
        "model": MODEL,
        "architecture": "three_pass_falsifying",
        "required_passes": list(multipass.REQUIRED_PASSES),
        "historical_cases": historical_ok,
        "historical_detected": sum(historical_ok.values()),
        "historical_total": len(HISTORICAL_CASES),
        "negative_control": "CLEAN_NON_BLOCKING" if negative_control_ok else "FAILED",
        "cases": cases,
        "result": "QUALIFIED_FOR_REPEAT" if qualified else "NOT_QUALIFIED",
        "authority": "INFERENCE_ONLY",
        "note": "A single qualified run does not authorize provider migration or merge eligibility.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    valid = sub.add_parser("record-valid")
    valid.add_argument("--case", required=True, choices=ALL_CASES)
    valid.add_argument("--pass-id", required=True, choices=multipass.REQUIRED_PASSES)
    valid.add_argument("--decision", required=True, type=Path)
    valid.add_argument("--out", required=True, type=Path)

    failure = sub.add_parser("record-failure")
    failure.add_argument("--case", required=True, choices=ALL_CASES)
    failure.add_argument("--pass-id", required=True, choices=multipass.REQUIRED_PASSES)
    failure.add_argument(
        "--status",
        required=True,
        choices=("PROVIDER_FAILURE", "MODEL_OUTPUT_INVALID"),
    )
    failure.add_argument("--reason", required=True)
    failure.add_argument("--out", required=True, type=Path)

    summary = sub.add_parser("summarize")
    summary.add_argument("--root", required=True, type=Path)
    summary.add_argument("--out", required=True, type=Path)

    args = parser.parse_args()
    if args.command == "record-valid":
        result = valid_record(args.case, args.pass_id, args.decision)
    elif args.command == "record-failure":
        result = failure_record(args.case, args.pass_id, args.status, args.reason)
    else:
        result = summarize(args.root)
    _write(args.out, result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
