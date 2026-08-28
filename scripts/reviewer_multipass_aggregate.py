#!/usr/bin/env python3
"""Deterministically aggregate independent Reviewer passes for PolaCore #65.

This module is deliberately offline. It does not invoke models, access credentials,
use the network, score the blind corpus, or authorize publication/merge actions.
It consumes pass records that have already crossed their pass-specific transport
and Reviewer output validation boundary.

Aggregation is fail-closed:
- exactly one record is required for every trusted review dimension;
- missing, duplicate, unexpected, malformed, provider-failed, or invalid-output
  records make the aggregate UNPROVEN and blocking;
- valid blocking evidence cannot be outvoted by non-blocking passes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "polacore.reviewer-multipass-aggregate/v1"
PASS_SCHEMA = "polacore.reviewer-multipass-pass/v1"
REQUIRED_PASSES = (
    "behavioral_semantics",
    "implementation_consistency",
    "security_authority",
)
VALID_STATUSES = {"VALID", "PROVIDER_FAILURE", "MODEL_OUTPUT_INVALID"}
VALID_VERDICTS = {"READY_FOR_HUMAN", "CHANGES_REQUIRED", "BLOCKED"}
BLOCKING_VERDICTS = {"CHANGES_REQUIRED", "BLOCKED"}


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _clean_reason(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:500]


def _normalize_record(raw: object) -> tuple[dict[str, Any] | None, str]:
    if not isinstance(raw, dict):
        return None, "pass record must be an object"
    if raw.get("schema") != PASS_SCHEMA:
        return None, "pass record schema is invalid"

    case = raw.get("case")
    pass_id = raw.get("pass_id")
    status = raw.get("status")
    if not isinstance(case, str) or not case:
        return None, "pass record case is invalid"
    if pass_id not in REQUIRED_PASSES:
        return None, "pass record id is unexpected"
    if status not in VALID_STATUSES:
        return None, "pass record status is invalid"

    normalized: dict[str, Any] = {
        "schema": PASS_SCHEMA,
        "case": case,
        "pass_id": pass_id,
        "status": status,
    }
    if status == "VALID":
        decision = raw.get("decision")
        if not isinstance(decision, dict):
            return None, "valid pass decision must be an object"
        verdict = decision.get("verdict")
        confidence = decision.get("confidence")
        rationale = decision.get("rationale")
        if verdict not in VALID_VERDICTS:
            return None, "valid pass verdict is invalid"
        if (
            not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not 0.0 <= float(confidence) <= 1.0
        ):
            return None, "valid pass confidence is invalid"
        if not isinstance(rationale, str) or not 20 <= len(rationale) <= 800:
            return None, "valid pass rationale length is invalid"
        # Preserve the existing Reviewer fail-closed confidence contract even if
        # a caller accidentally presents a record that skipped the validator.
        if float(confidence) < 0.60 and verdict != "BLOCKED":
            return None, "low-confidence valid pass must be BLOCKED"
        normalized["decision"] = {
            "verdict": verdict,
            "confidence": float(confidence),
            "rationale": rationale,
        }
    else:
        reason = _clean_reason(raw.get("reason"))
        if not reason:
            return None, "failed pass reason is missing"
        normalized["reason"] = reason
    return normalized, ""


def aggregate(records: list[object]) -> dict[str, Any]:
    normalized: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, raw in enumerate(records):
        row, error = _normalize_record(raw)
        if row is None:
            errors.append(f"input[{index}]: {error}")
        else:
            normalized.append(row)

    by_pass: dict[str, list[dict[str, Any]]] = {
        name: [] for name in REQUIRED_PASSES
    }
    for row in normalized:
        by_pass[str(row["pass_id"])].append(row)

    duplicate = sorted(name for name, rows in by_pass.items() if len(rows) > 1)
    missing = sorted(name for name, rows in by_pass.items() if len(rows) == 0)
    if duplicate:
        errors.append("duplicate pass ids: " + ",".join(duplicate))
    if missing:
        errors.append("missing pass ids: " + ",".join(missing))

    cases = sorted({str(row["case"]) for row in normalized})
    if len(cases) != 1:
        errors.append("pass records must bind to exactly one case")
    case = cases[0] if len(cases) == 1 else None

    ordered_rows = [
        by_pass[name][0]
        for name in REQUIRED_PASSES
        if len(by_pass[name]) == 1
    ]
    pass_digests = {row["pass_id"]: _digest(row) for row in ordered_rows}
    failed = sorted(
        str(row["pass_id"])
        for row in ordered_rows
        if row.get("status") != "VALID"
    )
    valid_rows = [row for row in ordered_rows if row.get("status") == "VALID"]
    blocking = sorted(
        str(row["pass_id"])
        for row in valid_rows
        if row["decision"]["verdict"] in BLOCKING_VERDICTS
    )

    complete = (
        not errors
        and not failed
        and len(valid_rows) == len(REQUIRED_PASSES)
    )
    status = "COMPLETE" if complete else "UNPROVEN"
    disposition = "BLOCKING" if (not complete or blocking) else "NON_BLOCKING"

    if complete:
        verdicts = [row["decision"]["verdict"] for row in valid_rows]
        if "BLOCKED" in verdicts:
            aggregate_verdict = "BLOCKED"
        elif "CHANGES_REQUIRED" in verdicts:
            aggregate_verdict = "CHANGES_REQUIRED"
        else:
            aggregate_verdict = "READY_FOR_HUMAN"
        confidence_floor = min(
            float(row["decision"]["confidence"]) for row in valid_rows
        )
    else:
        aggregate_verdict = "BLOCKED"
        confidence_floor = 0.0

    result = {
        "schema": SCHEMA,
        "case": case,
        "required_passes": list(REQUIRED_PASSES),
        "status": status,
        "disposition": disposition,
        "aggregate_verdict": aggregate_verdict,
        "confidence_floor": confidence_floor,
        "blocking_passes": blocking,
        "failed_passes": failed,
        "errors": errors,
        "pass_digests": pass_digests,
        "authority": "INFERENCE_ONLY",
    }
    result["aggregate_digest"] = _digest(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs="+", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    rows = [json.loads(path.read_text(encoding="utf-8")) for path in args.inputs]
    result = aggregate(rows)
    args.out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
