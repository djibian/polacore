#!/usr/bin/env python3
"""Validate a PolaCore A0-maintenance classifier response.

The model is advisory only. This validator accepts exactly one terminal decision
and converts low-confidence repair claims to rejection by contract.
"""
from __future__ import annotations

import json
import pathlib
import sys

ALLOWED = {"A0_REPAIRABLE", "ESCALATE"}
EXPECTED_KEYS = {"classification", "confidence", "rationale"}
DSML_SUFFIX = "</parameter>\n</｜DSML｜invoke>\n</｜DSML｜tool_calls>"


def fail(message: str) -> None:
    raise SystemExit(f"a0 classifier output rejected: {message}")


def last_text(path: pathlib.Path) -> str:
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
        fail("no text event found")
    return texts[-1]


def extract(raw: str) -> object:
    if raw.startswith("```") or raw.endswith("```"):
        fail("Markdown/code fences are forbidden")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    if raw.endswith(DSML_SUFFIX):
        raw = raw[: -len(DSML_SUFFIX)].rstrip()

    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if not lines:
        fail("final text is empty")
    candidate = lines[-1]
    if not (candidate.startswith("{") and candidate.endswith("}")):
        fail("terminal non-empty line is not a JSON object")
    if '"classification"' in "\n".join(lines[:-1]):
        fail("multiple decision-shaped outputs are forbidden")
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        fail(f"terminal decision is invalid JSON: {exc}")


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: agent_a0_classify_validate.py OPEN_CODE_JSONL OUTPUT_JSON")
    decision = extract(last_text(pathlib.Path(sys.argv[1])))
    if not isinstance(decision, dict) or set(decision) != EXPECTED_KEYS:
        fail(f"expected exactly keys {sorted(EXPECTED_KEYS)}")
    classification = decision["classification"]
    confidence = decision["confidence"]
    rationale = decision["rationale"]
    if classification not in ALLOWED:
        fail("unsupported classification")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        fail("confidence must be numeric")
    confidence = float(confidence)
    if not 0 <= confidence <= 1:
        fail("confidence out of range")
    if not isinstance(rationale, str):
        fail("rationale must be a string")
    rationale = " ".join(rationale.split())
    if not 20 <= len(rationale) <= 600:
        fail("rationale must contain 20-600 characters")
    if classification == "A0_REPAIRABLE" and confidence < 0.75:
        fail("A0_REPAIRABLE requires confidence >= 0.75")
    validated = {
        "classification": classification,
        "confidence": round(confidence, 4),
        "rationale": rationale,
    }
    pathlib.Path(sys.argv[2]).write_text(json.dumps(validated, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(validated))


if __name__ == "__main__":
    main()
