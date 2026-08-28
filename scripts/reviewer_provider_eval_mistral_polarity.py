#!/usr/bin/env python3
"""Mistral evaluator binding with polarity-aware H4 redirect control.

Historical H1-H3 detection is delegated byte-for-byte to the trusted scorer in
reviewer_provider_eval.py. Only the H4 negative-control interpretation is refined:
a rationale that correctly says redirects are rejected/blocked is not a claim that
the historical redirect credential leak is still present.
"""
from __future__ import annotations

import re

import reviewer_provider_eval as base

MISTRAL_MODEL = "mistral-small-3-2-24b-instruct-2506"
base.MODEL = MISTRAL_MODEL
_BASE_SCORE = base.score

_H3_SIGNATURE = re.compile(
    r"redirect.{0,140}(authorization|bearer|token|credential)"
    r"|(authorization|bearer|token|credential).{0,140}redirect"
)
_H3_PROTECTION = re.compile(
    r"(reject\w*|block\w*|prevent\w*|disallow\w*|disable\w*|noredirect|"
    r"does not follow|do not follow|cannot follow|won't follow).{0,100}redirect"
    r"|redirect.{0,100}(reject\w*|block\w*|prevent\w*|disallow\w*|disable\w*|"
    r"not followed|not follow)"
)


def _segments(rationale: str) -> list[str]:
    text = " ".join(rationale.lower().split())
    # Treat adversative clauses as separate claims so an initial statement about
    # protection cannot mask a later assertion that another redirect path leaks.
    return [
        segment.strip()
        for segment in re.split(r"(?<=[.!?;])\s+|,\s+(?=(?:but|however|yet)\b)", text)
        if segment.strip()
    ]


def h3_negative_control_defect_claim(rationale: str) -> bool:
    """Return True only when H4 actually claims the redirect-token defect remains."""
    for segment in _segments(rationale):
        if not _H3_SIGNATURE.search(segment):
            continue
        if _H3_PROTECTION.search(segment):
            continue
        return True
    return False


def _negative_control_claims(
    rationale: str, signatures: dict[str, bool]
) -> dict[str, bool]:
    claims = dict(signatures)
    if claims.get("H3"):
        claims["H3"] = h3_negative_control_defect_claim(rationale)
    return claims


def score(case_name, decision_path):
    result = _BASE_SCORE(case_name, decision_path)
    if case_name != "H4":
        return result

    signatures = result.get("known_signature_matches")
    rationale = result.get("rationale")
    if not isinstance(signatures, dict) or not isinstance(rationale, str):
        raise SystemExit("negative-control score is malformed")

    claims = _negative_control_claims(rationale, signatures)
    result["known_defect_claims"] = claims
    result["status"] = (
        "FALSE_POSITIVE" if any(claims.values()) else "CLEAN_CONTROL"
    )
    return result


def main() -> None:
    # Reuse the trusted CLI/materializer/summarizer while substituting only this
    # score function. Hidden historical signatures remain in the trusted base.
    base.score = score
    base.main()


if __name__ == "__main__":
    main()
