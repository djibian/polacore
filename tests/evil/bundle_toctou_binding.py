#!/usr/bin/env python3
"""Demonstrate why validating an OCI rootfs path and reopening it later is unsafe.

The test intentionally validates rootfs A, atomically replaces the path with B,
and proves that a path-based runtime reopen sees B while an already-open O_PATH
handle remains bound to A. This is a regression/evidence test, not the final
launcher binding mechanism.
"""
import os
import tempfile
from pathlib import Path


def identity(path: Path):
    st = os.stat(path, follow_symlinks=False)
    return st.st_dev, st.st_ino


def fd_identity(fd: int):
    st = os.fstat(fd)
    return st.st_dev, st.st_ino


def main():
    if not hasattr(os, "O_PATH"):
        raise SystemExit("SKIP: O_PATH unavailable on this platform")

    with tempfile.TemporaryDirectory(prefix="polacore-toctou-") as td:
        bundle = Path(td)
        root = bundle / "rootfs"
        attacker = bundle / "evil-rootfs"
        old = bundle / "validated-rootfs"
        root.mkdir()
        attacker.mkdir()
        (root / "IDENTITY").write_text("A\n")
        (attacker / "IDENTITY").write_text("B\n")

        validated = identity(root)
        fd = os.open(root, os.O_PATH | os.O_DIRECTORY | os.O_CLOEXEC)
        try:
            assert fd_identity(fd) == validated

            # Attacker swaps the pathname after validation.
            os.rename(root, old)
            os.rename(attacker, root)

            reopened = identity(root)
            assert reopened != validated, "path reopen unexpectedly retained validated object"
            assert (root / "IDENTITY").read_text() == "B\n"

            # The open file description still names the validated directory A.
            assert fd_identity(fd) == validated, "O_PATH handle lost object identity"
            assert (old / "IDENTITY").read_text() == "A\n"
        finally:
            os.close(fd)

    print("PASS: path reopen is TOCTOU-vulnerable; retained O_PATH identity is stable")


if __name__ == "__main__":
    main()
