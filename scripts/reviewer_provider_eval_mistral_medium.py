#!/usr/bin/env python3
"""Mistral Medium 3.5 binding for the trusted PolaCore #65 blind evaluator.

The scorer expectations and materialization logic remain defined only in
reviewer_provider_eval.py. This wrapper changes evidence identity, not scoring.
"""
from __future__ import annotations

import reviewer_provider_eval as base

MISTRAL_MEDIUM_MODEL = "Mistral-Medium-3.5-128B"
base.MODEL = MISTRAL_MEDIUM_MODEL


if __name__ == "__main__":
    base.main()
