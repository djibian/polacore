#!/usr/bin/env python3
"""GPT-OSS 120B binding for the trusted PolaCore #65 blind evaluator.

The scorer expectations and materialization logic remain defined only in
reviewer_provider_eval.py. This wrapper changes evidence identity, not scoring.
"""
from __future__ import annotations

import reviewer_provider_eval as base

GPTOSS_MODEL = "openai/gpt-oss-120b"
base.MODEL = GPTOSS_MODEL


if __name__ == "__main__":
    base.main()
