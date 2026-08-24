#!/usr/bin/env python3
"""Validate an OpenCode JSONL Router response and derive a deterministic state transition."""

from __future__ import annotations

import json
import pathlib
import sys

ALLOWED = {"NORMAL", "EXPERIMENTAL", "HIGH_RISK", "BLOCKED"}
STATE = {
    "NORMAL": "agent:ready-for-build",
    "EXPERIMENTAL": "agent:needs-experiment",
    "HIGH_RISK": "agent:needs-experiment",
    "BLOCKED": "agent:blocked",
}
RISK = {
    "NORMAL": "risk:normal",
    "EXPERIMENTAL": "risk:experimental",
    "HIGH_RISK": "risk:high",
    "BLOCKED": "risk:unknown",
}
EXPECTED_KEYS = {"classification", "confidence", "rationale"}


def fail(message: str) -> None:
    raise SystemExit(f"router output rejected: {message}")


def extract_last_text(path: pathlib.Path) -> str:
    texts: list[str] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError as exc:
            fail(f"invalid OpenCode JSONL on line {line_no}: {exc}")
        if event.get("type") == "text":
            part = event.get("part") or {}
            text = part.get("text")
            if isinstance(text, str):
                texts.append(text.strip())
    if not texts:
        fail("no final text event found")
    return texts[-1]


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: agent_router_validate.py OPEN_CODE_JSONL OUTPUT_JSON")

    raw_text = extract_last_text(pathlib.Path(sys.argv[1]))
    if raw_text.startswith("```") or raw_text.endswith("```"):
        fail("Markdown/code fences are forbidden")

    try:
        decision = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        fail(f"final text is not a JSON object: {exc}")

    if not isinstance(decision, dict):
        fail("final JSON must be an object")
    if set(decision) != EXPECTED_KEYS:
        fail(f"expected exactly keys {sorted(EXPECTED_KEYS)}")

    classification = decision["classification"]
    confidence = decision["confidence"]
    rationale = decision["rationale"]

    if classification not in ALLOWED:
        fail(f"unsupported classification: {classification!r}")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        fail("confidence must be numeric")
    if not 0.0 <= float(confidence) <= 1.0:
        fail("confidence must be between 0 and 1")
    if not isinstance(rationale, str):
        fail("rationale must be a string")
    rationale = " ".join(rationale.split())
    if not 20 <= len(rationale) <= 800:
        fail("rationale must contain 20-800 characters")
    if float(confidence) < 0.60 and classification != "BLOCKED":
        fail("confidence below 0.60 must route to BLOCKED")

    validated = {
        "classification": classification,
        "confidence": round(float(confidence), 4),
        "rationale": rationale,
        "state_label": STATE[classification],
        "risk_label": RISK[classification],
    }
    pathlib.Path(sys.argv[2]).write_text(
        json.dumps(validated, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(validated, ensure_ascii=False))


if __name__ == "__main__":
    main()
