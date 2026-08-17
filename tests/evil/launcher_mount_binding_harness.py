#!/usr/bin/env python3
"""Privileged launcher harness for fd-bound rootfs identity.

When CAP_SYS_ADMIN is available, this proves the intended TCB ordering:
  validated rootfs A -> open_tree detached mount -> pathname swap to B
  -> move_mount by fd -> attached tree is still A.

The probe also records CapEff before/after. It deliberately does not claim a
worker privilege-drop proof yet: that belongs in the real launcher process,
where mount authority is held only by the trusted parent and never inherited by
untrusted code.

CI commonly lacks CAP_SYS_ADMIN; EPERM/EACCES/ENOSYS is a clean SKIP.
"""
import ctypes
import errno
import os
import platform
import tempfile
from pathlib import Path

libc = ctypes.CDLL(None, use_errno=True)
AT_FDCWD = -100
OPEN_TREE_CLONE = 1
OPEN_TREE_CLOEXEC = os.O_CLOEXEC
MOVE_MOUNT_F_EMPTY_PATH = 0x4
SYS_OPEN_TREE = 428
SYS_MOVE_MOUNT = 429


def syscall(nr, *args):
    ret = libc.syscall(ctypes.c_long(nr), *args)
    if ret == -1:
        e = ctypes.get_errno()
        raise OSError(e, os.strerror(e))
    return ret


def cap_eff():
    for line in Path('/proc/self/status').read_text().splitlines():
        if line.startswith('CapEff:'):
            return int(line.split()[1], 16)
    raise RuntimeError('CapEff missing')


def main():
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'amd64'):
        print('SKIP: launcher mount harness targets Linux x86-64')
        return
    before = cap_eff()
    with tempfile.TemporaryDirectory(prefix='polacore-launcher-mount-') as td:
        base = Path(td)
        root, evil, old, target = [base / n for n in ('rootfs','evil-rootfs','validated-rootfs','attached')]
        for p in (root, evil, target): p.mkdir()
        (root/'IDENTITY').write_text('A\n')
        (evil/'IDENTITY').write_text('B\n')
        try:
            mfd = syscall(SYS_OPEN_TREE, ctypes.c_int(AT_FDCWD), ctypes.c_char_p(os.fsencode(root)), ctypes.c_uint(OPEN_TREE_CLONE|OPEN_TREE_CLOEXEC))
        except OSError as exc:
            if exc.errno in (errno.EPERM, errno.EACCES, errno.ENOSYS):
                print(f'SKIP: privileged detached-mount proof unavailable: {exc}; CapEff=0x{before:x}')
                return
            raise
        try:
            os.rename(root, old); os.rename(evil, root)
            assert (root/'IDENTITY').read_text() == 'B\n'
            syscall(SYS_MOVE_MOUNT, ctypes.c_int(mfd), ctypes.c_char_p(b''), ctypes.c_int(AT_FDCWD), ctypes.c_char_p(os.fsencode(target)), ctypes.c_uint(MOVE_MOUNT_F_EMPTY_PATH))
            assert (target/'IDENTITY').read_text() == 'A\n'
            after = cap_eff()
            assert before == after, 'probe unexpectedly changed capability state'
        finally:
            os.close(mfd)
    print(f'PASS: trusted mount object stayed bound to A across pathname swap; CapEff=0x{before:x}')

if __name__ == '__main__': main()
