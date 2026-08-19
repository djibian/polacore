#!/bin/sh
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
bin=$(mktemp /tmp/p117-openat2.XXXXXX)
mount_base=
cleanup() {
    if [ -n "$mount_base" ]; then
        umount "$mount_base/staging/mounted" 2>/dev/null || true
        rm -rf "$mount_base"
    fi
    rm -f "$bin"
}
trap cleanup EXIT HUP INT TERM

${CC:-cc} -std=c11 -Wall -Wextra -Werror -O2 "$here/openat2_beneath.c" -o "$bin"
"$bin"

# Exercise NO_XDEV separately. Most containers deliberately lack CAP_SYS_ADMIN.
mount_base=$(mktemp -d /tmp/p117-mount.XXXXXX)
mkdir -p "$mount_base/staging/mounted" "$mount_base/outside"
printf 'OUTSIDE_MOUNT\n' > "$mount_base/outside/secret"
if mount --bind "$mount_base/outside" "$mount_base/staging/mounted" 2>/dev/null; then
    if "$bin" --mount-probe "$mount_base/staging"; then
        echo 'PASS mount crossing denied by RESOLVE_NO_XDEV'
    else
        echo 'FAIL mount crossing was readable' >&2
        exit 1
    fi
else
    echo 'UNPROVEN mount crossing: environment cannot create a bind mount (CAP_SYS_ADMIN unavailable)'
fi
