#!/usr/bin/env python3
"""Validate an OpenCode JSONL Reviewer response and derive a deterministic review state.

Reviewer prose is never authoritative. The validator accepts either an exact JSON
final text (the original contract) or, for models that emit non-authoritative
review narration, exactly one decision-shaped JSON object on the final non-empty
line. Any earlier decision-shaped JSON is rejected. Only the validated terminal
object can drive repository state.
"""

from __future__ import annotations

import json
import pathlib
import sys

ALLOWED = {"READY_FOR_HUMAN", "CHANGES_REQUIRED", "BLOCKED"}
EXPECTED_KEYS = {"verdict", "confidence", "rationale"}


def fail(message: str) -> None:
    raise SystemExit(f"reviewer output rejected: {message}")


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


def extract_decision(raw_text: str) -> object:
    """Return the sole authoritative JSON decision from the final model text.

    Prefer the historical strict contract where the complete final text is JSON.
    If that fails, permit non-authoritative prose only before a terminal JSON
    object. A previous line containing a decision-shaped `verdict` key is
    rejected so the controller never chooses between competing model decisions.
    """
    if raw_text.startswith("```") or raw_text.endswith("```"):
        fail("Markdown/code fences are forbidden")

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    if not lines:
        fail("final text is empty")

    candidate = lines[-1]
    if not (candidate.startswith("{") and candidate.endswith("}")):
        fail("final non-empty line is not a JSON object")
    if '"verdict"' in "\n".join(lines[:-1]):
        fail("multiple decision-shaped outputs are forbidden")
    if candidate.startswith("```") or candidate.endswith("```"):
        fail("Markdown/code fences are forbidden")

    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        fail(f"terminal JSON decision is invalid: {exc}")


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: agent_reviewer_validate.py OPEN_CODE_JSONL OUTPUT_JSON")

    raw_text = extract_last_text(pathlib.Path(sys.argv[1]))
    decision = extract_decision(raw_text)

    if not isinstance(decision, dict):
        fail("final JSON must be an object")
    if set(decision) != EXPECTED_KEYS:
        fail(f"expected exactly keys {sorted(EXPECTED_KEYS)}")

    verdict = decision["verdict"]
    confidence = decision["confidence"]
    rationale = decision["rationale"]

    if verdict not in ALLOWED:
        fail(f"unsupported verdict: {verdict!r}")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        fail("confidence must be numeric")
    if not 0.0 <= float(confidence) <= 1.0:
        fail("confidence must be between 0 and 1")
    if not isinstance(rationale, str):
        fail("rationale must be a string")
    rationale = " ".join(rationale.split())
    if not 20 <= len(rationale) <= 800:
        fail("rationale must contain 20-800 characters")
    if float(confidence) < 0.60 and verdict != "BLOCKED":
        fail("confidence below 0.60 must produce BLOCKED")

    validated = {
        "verdict": verdict,
        "confidence": round(float(confidence), 4),
        "rationale": rationale,
    }
    pathlib.Path(sys.argv[2]).write_text(
        json.dumps(validated, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(validated, ensure_ascii=False))


if __name__ == "__main__":
    main()
