#!/usr/bin/env python3
"""GPT-OSS binding for the trusted schema-constrained Albert Reviewer transport."""
from __future__ import annotations

import reviewer_provider_structured_transport as base

GPTOSS_MODEL = "openai/gpt-oss-120b"
base.MODEL = GPTOSS_MODEL


if __name__ == "__main__":
    base.main()
