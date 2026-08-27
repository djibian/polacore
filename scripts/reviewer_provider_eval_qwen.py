#!/usr/bin/env python3
"""Qwen3-Coder binding for the trusted PolaCore #65 blind evaluator.

The scorer expectations and materialization logic remain defined only in
reviewer_provider_eval.py. This wrapper changes evidence identity, not scoring.
"""
from __future__ import annotations

import reviewer_provider_eval as base

QWEN_MODEL = "qwen3-coder-30b-A3b-instruct"
base.MODEL = QWEN_MODEL


if __name__ == "__main__":
    base.main()
