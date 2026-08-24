#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SOURCES = sorted(ROOT.glob("*.rs"))

forbidden = {
    r"\bassume\s*\(": "assume(...) shortcut",
    r"\badmit\s*\(": "admit(...) shortcut",
    r"external_body": "external_body verification bypass",
    r"#\s*\[\s*verifier::external\b": "verifier::external bypass",
    r"\baxiom\b": "axiom shortcut",
    r"assume_specification": "assumed external specification",
}

failed = False
boundary_count = 0

for source in SOURCES:
    text = source.read_text(encoding="utf-8")

    for pattern, description in forbidden.items():
        match = re.search(pattern, text)
        if match:
            line = text.count("\n", 0, match.start()) + 1
            print(f"REFUTED hygiene: {description} at {source}:{line}", file=sys.stderr)
            failed = True

    # Any marker whose name begins with UNTRUSTED_BOUNDARY is a public hostile
    # call boundary. It must not rely on a Verus-only caller precondition.
    for match in re.finditer(r"UNTRUSTED_BOUNDARY(?:_[A-Z0-9]+)?", text):
        boundary_count += 1
        fn_pos = text.find("fn ", match.end())
        body_pos = text.find("{", fn_pos)
        if fn_pos == -1 or body_pos == -1:
            print(
                f"REFUTED hygiene: boundary marker in {source} has no following function",
                file=sys.stderr,
            )
            failed = True
            continue
        signature = text[fn_pos:body_pos]
        if re.search(r"\brequires\b", signature):
            line = text.count("\n", 0, fn_pos) + 1
            print(
                f"REFUTED hygiene: hostile boundary trusts caller preconditions at {source}:{line}",
                file=sys.stderr,
            )
            failed = True

if not SOURCES:
    print("REFUTED hygiene: no Verus experiment sources found", file=sys.stderr)
    failed = True

if boundary_count < 3:
    print(
        f"REFUTED hygiene: expected at least three hostile-boundary markers; found {boundary_count}",
        file=sys.stderr,
    )
    failed = True

if failed:
    sys.exit(1)

print(
    f"VERIFIED_BY_CI proof-hygiene guard: scanned {len(SOURCES)} source(s), "
    f"{boundary_count} hostile boundary/boundaries, no selected proof shortcuts"
)
