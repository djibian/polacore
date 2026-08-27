#!/usr/bin/env python3
"""GPT-OSS binding for the trusted schema-constrained Albert Reviewer transport."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import reviewer_provider_structured_transport as base

GPTOSS_MODEL = "openai/gpt-oss-120b"
base.MODEL = GPTOSS_MODEL


def _finish_reason_from_extract_args() -> str:
    """Return only the provider envelope's finish_reason, never model content."""
    try:
        if len(sys.argv) < 2 or sys.argv[1] != "extract-response":
            return "UNAVAILABLE"
        response_index = sys.argv.index("--response") + 1
        response_path = Path(sys.argv[response_index])
        payload = json.loads(response_path.read_text(encoding="utf-8"))
        choices = payload.get("choices") if isinstance(payload, dict) else None
        if not isinstance(choices, list) or len(choices) != 1:
            return "UNAVAILABLE"
        choice = choices[0]
        if not isinstance(choice, dict):
            return "UNAVAILABLE"
        finish_reason = choice.get("finish_reason")
        if finish_reason is None or isinstance(finish_reason, (str, int, float, bool)):
            rendered = json.dumps(finish_reason, ensure_ascii=True, separators=(",", ":"))
            return rendered[:120]
        return f"<{type(finish_reason).__name__}>"
    except (OSError, ValueError, IndexError, json.JSONDecodeError):
        return "UNAVAILABLE"


def main() -> None:
    try:
        base.main()
    except ValueError as exc:
        # Preserve the same fail-closed rejection while surfacing only the
        # structural reason and envelope finish_reason. Never read or print
        # provider/model message content here.
        finish_reason = _finish_reason_from_extract_args()
        print(
            f"structured extraction rejected: {exc}; finish_reason={finish_reason}",
            file=sys.stderr,
        )
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
