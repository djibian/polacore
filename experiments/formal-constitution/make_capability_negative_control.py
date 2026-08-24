#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

SOURCE = Path(__file__).with_name("capability_kernel.rs")
TARGET = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/capability-kernel-broken.rs")

text = SOURCE.read_text(encoding="utf-8")
anchor = "pub fn authorize_request("
head, separator, tail = text.partition(anchor)
if not separator:
    raise SystemExit("negative-control setup failed: authorize_request() not found")

safe = """            && req.capability_id == self.grant_id
            && req.caller == self.grant_subject
            && req.resource == self.grant_resource
"""
broken = """            && req.capability_id == self.grant_id
            // NEGATIVE CONTROL: subject binding deliberately removed.
            && req.resource == self.grant_resource
"""

if tail.count(safe) != 1:
    raise SystemExit(
        f"negative-control setup failed: expected one request subject-binding block, found {tail.count(safe)}"
    )

tail = tail.replace(safe, broken, 1)
TARGET.write_text(head + separator + tail, encoding="utf-8")
print(TARGET)
