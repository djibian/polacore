#!/usr/bin/env python3
"""Probe the Linux fd-based mount primitive proposed for validated rootfs binding.

This is deliberately a capability probe, not a claim that OCI launch is bound yet.
It demonstrates the useful semantic when the host grants CAP_SYS_ADMIN: clone a
validated directory into a detached mount object with open_tree(OPEN_TREE_CLONE),
then attach that mount by fd with move_mount(MOVE_MOUNT_F_EMPTY_PATH). A pathname
swap after cloning must not change the mounted tree.

CI environments commonly lack CAP_SYS_ADMIN. In that case this probe reports a
clean SKIP while the non-privileged O_PATH TOCTOU regression remains mandatory.
"""
import ctypes
import errno
import os
import platform
import tempfile
from pathlib import Path

libc = ctypes.CDLL(None, use_errno=True)

# Linux UAPI constants.
OPEN_TREE_CLONE = 1
OPEN_TREE_CLOEXEC = os.O_CLOEXEC
MOVE_MOUNT_F_EMPTY_PATH = 0x00000004
AT_FDCWD = -100

# Syscall numbers for the Standard v0 target (Linux x86-64).
SYS_OPEN_TREE = 428
SYS_MOVE_MOUNT = 429


def syscall(nr, *args):
    ret = libc.syscall(ctypes.c_long(nr), *args)
    if ret == -1:
        e = ctypes.get_errno()
        raise OSError(e, os.strerror(e))
    return ret


def open_tree(path: Path) -> int:
    return syscall(
        SYS_OPEN_TREE,
        ctypes.c_int(AT_FDCWD),
        ctypes.c_char_p(os.fsencode(path)),
        ctypes.c_uint(OPEN_TREE_CLONE | OPEN_TREE_CLOEXEC),
    )


def move_mount(mount_fd: int, target: Path) -> None:
    syscall(
        SYS_MOVE_MOUNT,
        ctypes.c_int(mount_fd),
        ctypes.c_char_p(b""),
        ctypes.c_int(AT_FDCWD),
        ctypes.c_char_p(os.fsencode(target)),
        ctypes.c_uint(MOVE_MOUNT_F_EMPTY_PATH),
    )


def main():
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "amd64"):
        print("SKIP: fd-based mount probe currently targets Linux x86-64")
        return

    with tempfile.TemporaryDirectory(prefix="polacore-mountfd-") as td:
        base = Path(td)
        root = base / "rootfs"
        evil = base / "evil-rootfs"
        old = base / "validated-rootfs"
        target = base / "attached"
        for p in (root, evil, target):
            p.mkdir()
        (root / "IDENTITY").write_text("A\n")
        (evil / "IDENTITY").write_text("B\n")

        try:
            mfd = open_tree(root)
        except OSError as exc:
            if exc.errno in (errno.EPERM, errno.EACCES, errno.ENOSYS):
                print(f"SKIP: open_tree(OPEN_TREE_CLONE) unavailable/unprivileged: {exc}")
                return
            raise

        try:
            # Swap the source pathname only after the detached mount object exists.
            os.rename(root, old)
            os.rename(evil, root)
            assert (root / "IDENTITY").read_text() == "B\n"

            move_mount(mfd, target)
            assert (target / "IDENTITY").read_text() == "A\n", (
                "fd-bound detached mount followed the swapped pathname"
            )
        finally:
            os.close(mfd)

    print("PASS: detached open_tree mount remained bound to validated tree across path swap")


if __name__ == "__main__":
    main()
