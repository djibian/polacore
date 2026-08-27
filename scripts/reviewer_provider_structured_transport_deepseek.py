#!/usr/bin/env python3
"""DeepSeek binding for the trusted schema-constrained Albert Reviewer transport."""
from __future__ import annotations

import reviewer_provider_structured_transport as base

DEEPSEEK_MODEL = "deepseek-v4-flash"
base.MODEL = DEEPSEEK_MODEL


if __name__ == "__main__":
    base.main()
