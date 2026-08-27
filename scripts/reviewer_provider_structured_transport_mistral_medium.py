#!/usr/bin/env python3
"""Mistral Medium 3.5 binding for the trusted schema-constrained Albert Reviewer transport."""
from __future__ import annotations

import reviewer_provider_structured_transport as base

MISTRAL_MEDIUM_MODEL = "Mistral-Medium-3.5-128B"
base.MODEL = MISTRAL_MEDIUM_MODEL


if __name__ == "__main__":
    base.main()
