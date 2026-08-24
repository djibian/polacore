#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

SOURCE = Path(__file__).with_name("constitution.rs")
text = SOURCE.read_text(encoding="utf-8")

forbidden = {
    r"\bassume\s*\(": "assume(...) shortcut",
    r"\badmit\s*\(": "admit(...) shortcut",
    r"external_body": "external_body verification bypass",
    r"#\s*\[\s*verifier::external\b": "verifier::external bypass",
    r"\baxiom\b": "axiom shortcut",
    r"assume_specification": "assumed external specification",
}

failed = False
for pattern, description in forbidden.items():
    match = re.search(pattern, text)
    if match:
        line = text.count("\n", 0, match.start()) + 1
        print(f"REFUTED hygiene: {description} at {SOURCE}:{line}", file=sys.stderr)
        failed = True

marker = "UNTRUSTED_BOUNDARY"
if text.count(marker) != 2:
    print(
        f"REFUTED hygiene: expected exactly two {marker} markers; found {text.count(marker)}",
        file=sys.stderr,
    )
    failed = True

# The experiment's core integration question is whether hostile callers can invoke
# the boundary without needing to satisfy a Verus-only precondition. Check the
# signatures between each marker and opening body brace for an accidental
# `requires` clause. This does not replace semantic review.
for index, match in enumerate(re.finditer(marker, text), start=1):
    fn_pos = text.find("fn ", match.end())
    body_pos = text.find("{", fn_pos)
    if fn_pos == -1 or body_pos == -1:
        print(f"REFUTED hygiene: boundary #{index} function not found", file=sys.stderr)
        failed = True
        continue
    signature = text[fn_pos:body_pos]
    if re.search(r"\brequires\b", signature):
        print(
            f"REFUTED hygiene: boundary #{index} trusts caller preconditions",
            file=sys.stderr,
        )
        failed = True

if failed:
    sys.exit(1)

print("VERIFIED_BY_CI proof-hygiene guard: no forbidden shortcuts in experiment source")
