#!/usr/bin/env python3
"""Qwen binding for the trusted schema-constrained Albert Reviewer transport."""
from __future__ import annotations

import reviewer_provider_structured_transport as base

QWEN_MODEL = "qwen3-coder-30b-A3b-instruct"
base.MODEL = QWEN_MODEL


if __name__ == "__main__":
    base.main()
