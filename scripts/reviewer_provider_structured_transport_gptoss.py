#!/usr/bin/env python3
"""GPT-OSS binding for the trusted schema-constrained Albert Reviewer transport."""
from __future__ import annotations

import sys

import reviewer_provider_structured_transport as base

GPTOSS_MODEL = "openai/gpt-oss-120b"
base.MODEL = GPTOSS_MODEL


def main() -> None:
    try:
        base.main()
    except ValueError as exc:
        # Preserve the same fail-closed rejection while surfacing only the
        # structural reason. Never print provider/model content here.
        print(f"structured extraction rejected: {exc}", file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
