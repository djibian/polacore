#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

SOURCE = Path(__file__).with_name("constitution.rs")
TARGET = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/constitution-broken.rs")

text = SOURCE.read_text(encoding="utf-8")
anchor = "fn authorize("
head, separator, tail = text.partition(anchor)
if not separator:
    raise SystemExit("negative-control setup failed: authorize() not found")

safe = """    constitution
        && site_policy
        && capability_present
        && capability_epoch == current_epoch
        && current_epoch > 0
"""
broken = """    // NEGATIVE CONTROL: constitutional gate deliberately removed.
    site_policy
        && capability_present
        && capability_epoch == current_epoch
        && current_epoch > 0
"""

if tail.count(safe) != 1:
    raise SystemExit(
        f"negative-control setup failed: expected one authorize implementation, found {tail.count(safe)}"
    )

tail = tail.replace(safe, broken, 1)
TARGET.write_text(head + separator + tail, encoding="utf-8")
print(TARGET)
