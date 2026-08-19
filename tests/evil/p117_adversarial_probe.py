#!/usr/bin/env python3
"""Adversarial composition probe for the candidate P117 openat2 mechanism.

This is deliberately independent of the experiment implementation.  It tests
what an enumerator can safely infer after it has observed a directory entry,
and distinguishes escape resistance from object/path identity.
"""

import ctypes
import errno
import json
import os
import platform
import stat
import tempfile
from pathlib import Path


SYS_OPENAT2 = 437  # Linux x86-64
AT_FDCWD = -100
RESOLVE_NO_XDEV = 0x01
RESOLVE_NO_MAGICLINKS = 0x02
RESOLVE_NO_SYMLINKS = 0x04
RESOLVE_BENEATH = 0x08
O_PATH = getattr(os, "O_PATH", 0o10000000)


class OpenHow(ctypes.Structure):
    _fields_ = [("flags", ctypes.c_uint64), ("mode", ctypes.c_uint64), ("resolve", ctypes.c_uint64)]


libc = ctypes.CDLL(None, use_errno=True)


def openat2(dirfd, path, flags, resolve):
    how = OpenHow(flags, 0, resolve)
    result = libc.syscall(
        ctypes.c_long(SYS_OPENAT2), ctypes.c_int(dirfd),
        ctypes.c_char_p(os.fsencode(path)), ctypes.byref(how), ctypes.sizeof(how)
    )
    if result == -1:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), path)
    return result


def emit(case, classification, **evidence):
    print(json.dumps({"case": case, "classification": classification, **evidence}, sort_keys=True))


def main():
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "amd64"):
        emit("platform", "UNPROVEN", reason="probe requires Linux x86-64 openat2 syscall ABI")
        return 77

    resolve = RESOLVE_BENEATH | RESOLVE_NO_MAGICLINKS
    try:
        with tempfile.TemporaryDirectory(prefix="polacore-p117-adversary-") as temporary:
            base = Path(temporary)
            staging = base / "staging"
            outside = base / "outside"
            staging.mkdir()
            outside.mkdir()
            (staging / "entry").write_text("approved\n")
            (outside / "secret").write_text("outside\n")
            rootfd = os.open(staging, O_PATH | os.O_DIRECTORY | os.O_CLOEXEC)
            try:
                # An enumerator observed this name and object before an attacker
                # substituted another ordinary in-root object at the same name.
                observed = os.stat("entry", dir_fd=rootfd, follow_symlinks=False)
                replacement = staging / "replacement"
                replacement.write_text("substituted\n")
                os.replace(replacement, staging / "entry")
                fd = openat2(rootfd, "entry", os.O_RDONLY | os.O_CLOEXEC, resolve)
                try:
                    data = os.read(fd, 64).decode()
                    opened = os.fstat(fd)
                finally:
                    os.close(fd)
                assert data == "substituted\n"
                assert (observed.st_dev, observed.st_ino) != (opened.st_dev, opened.st_ino)
                emit(
                    "enumerate_then_open_substitution", "REFUTED",
                    claim="an enumerated path remains bound to the enumerated object",
                    observed_inode=[observed.st_dev, observed.st_ino],
                    opened_inode=[opened.st_dev, opened.st_ino], opened_data=data.strip(),
                    resolve=hex(resolve),
                )

                # The same composition still rejects an outside symlink escape.
                os.unlink(staging / "entry")
                os.symlink(outside / "secret", staging / "entry")
                try:
                    fd = openat2(rootfd, "entry", os.O_RDONLY | os.O_CLOEXEC, resolve)
                except OSError as exc:
                    assert exc.errno in (errno.EXDEV, errno.ELOOP)
                    emit("symlink_swap_escape", "PROVEN_BY_TEST", errno=exc.errno, resolve=hex(resolve))
                else:
                    os.close(fd)
                    raise AssertionError("openat2 followed a swapped symlink outside staging")

                # /proc/self/fd is a representative magic-link namespace.  It
                # is outside this root, so BENEATH must reject it independently
                # of whether the kernel reaches magic-link evaluation.
                os.unlink(staging / "entry")
                os.symlink("/proc/self/fd/0", staging / "entry")
                try:
                    fd = openat2(rootfd, "entry", O_PATH | os.O_CLOEXEC, resolve)
                except OSError as exc:
                    assert exc.errno in (errno.EXDEV, errno.ELOOP)
                    emit("magic_link_path", "PROVEN_BY_TEST", errno=exc.errno, resolve=hex(resolve))
                else:
                    os.close(fd)
                    raise AssertionError("openat2 resolved a proc magic-link path")

                # A FIFO is inside the root and therefore not rejected by path
                # resolution.  Enumeration/copy code needs an explicit object
                # type allowlist before a potentially blocking data open.
                os.unlink(staging / "entry")
                os.mkfifo(staging / "entry")
                fd = openat2(rootfd, "entry", O_PATH | os.O_CLOEXEC, resolve)
                try:
                    mode = os.fstat(fd).st_mode
                finally:
                    os.close(fd)
                assert stat.S_ISFIFO(mode)
                emit("fifo_special_object", "REFUTED", claim="resolution flags reject special objects", type="fifo")

                # A mount crossing cannot be manufactured honestly without mount
                # authority.  Probe capability by attempting a bind mount and
                # report inability as UNPROVEN rather than treating it as PASS.
                mountpoint = staging / "mountpoint"
                mountpoint.mkdir()
                result = os.system(
                    f"mount --bind {os.fsencode(outside).decode()} {os.fsencode(mountpoint).decode()} "
                    ">/dev/null 2>&1"
                )
                if result != 0:
                    emit("mount_crossing", "UNPROVEN", reason="bind mount denied or mount utility unavailable")
                else:
                    try:
                        fd = openat2(
                            rootfd, "mountpoint/secret", os.O_RDONLY | os.O_CLOEXEC,
                            resolve | RESOLVE_NO_XDEV,
                        )
                    except OSError as exc:
                        assert exc.errno == errno.EXDEV
                        emit("mount_crossing", "PROVEN_BY_TEST", errno=exc.errno, resolve=hex(resolve | RESOLVE_NO_XDEV))
                    else:
                        os.close(fd)
                        raise AssertionError("RESOLVE_NO_XDEV allowed a bind-mount crossing")
                    finally:
                        os.system(f"umount {os.fsencode(mountpoint).decode()} >/dev/null 2>&1")
            finally:
                os.close(rootfd)
    except OSError as exc:
        if exc.errno == errno.ENOSYS:
            emit("openat2", "UNPROVEN", errno=exc.errno, reason="kernel lacks openat2")
            return 77
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
