#!/usr/bin/env python3
"""Mistral Small 3.2 binding for the trusted PolaCore #65 blind evaluator.

The scorer expectations and materialization logic remain defined only in
reviewer_provider_eval.py. This wrapper changes evidence identity, not scoring.
"""
from __future__ import annotations

import reviewer_provider_eval as base

MISTRAL_MODEL = "mistral-small-3-2-24b-instruct-2506"
base.MODEL = MISTRAL_MODEL


if __name__ == "__main__":
    base.main()
