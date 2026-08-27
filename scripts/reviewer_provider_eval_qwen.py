#!/usr/bin/env python3
"""Qwen3-Coder binding for the trusted PolaCore #65 blind evaluator.

The scorer expectations and materialization logic remain defined only in
reviewer_provider_eval.py. This wrapper changes evidence identity and can build a
bounded tool-free prompt envelope; it never changes scoring expectations.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import reviewer_provider_eval as base

QWEN_MODEL = "qwen3-coder-30b-A3b-instruct"
BUNDLE_SCHEMA = "polacore.reviewer-prompt-bundle/v1"
MAX_BUNDLE_BYTES = 150_000
EVIDENCE_FILES = (
    "candidate.py",
    "candidate-tests.py",
    "candidate-provider.md",
    "candidate-diff.txt",
)
base.MODEL = QWEN_MODEL


def build_bundle(input_dir: pathlib.Path, out_path: pathlib.Path) -> None:
    context_path = input_dir / "reviewer-context.md"
    if not context_path.is_file():
        raise SystemExit("reviewer-context.md is missing")

    evidence: list[dict[str, str]] = []
    for name in EVIDENCE_FILES:
        path = input_dir / name
        if path.is_file():
            evidence.append(
                {
                    "path": f"agent-input/{name}",
                    "content": path.read_text(encoding="utf-8"),
                }
            )
    if not evidence:
        raise SystemExit("no materialized candidate evidence exists")

    payload = {
        "schema": BUNDLE_SCHEMA,
        "trusted_control": context_path.read_text(encoding="utf-8"),
        "untrusted_evidence": evidence,
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    size = len(encoded.encode("utf-8"))
    if size > MAX_BUNDLE_BYTES:
        raise SystemExit(f"reviewer prompt bundle exceeds {MAX_BUNDLE_BYTES} bytes")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(encoded, encoding="utf-8")
    print(json.dumps({"schema": BUNDLE_SCHEMA, "bytes": size, "paths": [x["path"] for x in evidence]}))


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "bundle":
        parser = argparse.ArgumentParser()
        parser.add_argument("bundle")
        parser.add_argument("--input", required=True, type=pathlib.Path)
        parser.add_argument("--out", required=True, type=pathlib.Path)
        args = parser.parse_args()
        build_bundle(args.input, args.out)
        return
    base.main()


if __name__ == "__main__":
    main()
