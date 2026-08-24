#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SOURCES = sorted(ROOT.glob("*.rs"))

# These names are part of the experiment contract. The scanner deliberately
# binds to them instead of trusting movable comments/markers.
BOUNDARIES = {
    "constitution.rs": ("authorize", "mediate_admin_transition"),
    "capability_kernel.rs": ("authorize_request",),
}

forbidden = {
    r"\bassume\s*\(": "assume(...) shortcut",
    r"\badmit\s*\(": "admit(...) shortcut",
    r"external_body": "external_body verification bypass",
    r"#\s*\[\s*verifier::external\b": "verifier::external bypass",
    r"\baxiom\b": "axiom shortcut",
    r"assume_specification": "assumed external specification",
}

failed = False

if not SOURCES:
    print("REFUTED hygiene: no Verus experiment sources found", file=sys.stderr)
    sys.exit(1)

for source in SOURCES:
    text = source.read_text(encoding="utf-8")

    for pattern, description in forbidden.items():
        match = re.search(pattern, text)
        if match:
            line = text.count("\n", 0, match.start()) + 1
            print(f"REFUTED hygiene: {description} at {source}:{line}", file=sys.stderr)
            failed = True

for filename, function_names in BOUNDARIES.items():
    source = ROOT / filename
    if not source.exists():
        print(f"REFUTED hygiene: required boundary source missing: {source}", file=sys.stderr)
        failed = True
        continue

    text = source.read_text(encoding="utf-8")
    for name in function_names:
        pattern = re.compile(rf"\bfn\s+{re.escape(name)}\s*\(")
        matches = list(pattern.finditer(text))
        if len(matches) != 1:
            print(
                f"REFUTED hygiene: expected exactly one function named {name} in {source}; "
                f"found {len(matches)}",
                file=sys.stderr,
            )
            failed = True
            continue

        match = matches[0]
        body_pos = text.find("{", match.end())
        if body_pos == -1:
            print(f"REFUTED hygiene: function {name} has no body in {source}", file=sys.stderr)
            failed = True
            continue

        signature = text[match.start():body_pos]
        if re.search(r"\brequires\b", signature):
            line = text.count("\n", 0, match.start()) + 1
            print(
                f"REFUTED hygiene: hostile boundary {name} trusts caller preconditions "
                f"at {source}:{line}",
                file=sys.stderr,
            )
            failed = True

if failed:
    sys.exit(1)

checked = sum(len(names) for names in BOUNDARIES.values())
print(
    f"VERIFIED_BY_CI proof-hygiene guard: scanned {len(SOURCES)} source(s), "
    f"checked {checked} named hostile boundaries, no selected proof shortcuts"
)
