#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
binary=$(mktemp /tmp/polacore-source-acquisition.XXXXXX)
mount_base=
cleanup() {
    if [ -n "$mount_base" ]; then
        umount "$mount_base/staging/mounted" 2>/dev/null || true
        rm -rf "$mount_base"
    fi
    rm -f "$binary"
}
trap cleanup EXIT HUP INT TERM

${CC:-cc} -std=c11 -Wall -Wextra -Werror -O2 \
    "$repo/security/source_acquisition.c" \
    "$repo/tests/evil/source_acquisition_test.c" -o "$binary"
"$binary"

mount_base=$(mktemp -d /tmp/polacore-acquire-mount.XXXXXX)
mkdir -p "$mount_base/staging/mounted" "$mount_base/outside"
printf 'OUTSIDE_MOUNT\n' > "$mount_base/outside/secret"
if mount --bind "$mount_base/outside" "$mount_base/staging/mounted" 2>/dev/null; then
    "$binary" --mount-probe "$mount_base/staging"
    echo 'PROVEN_BY_TEST mount crossing rejected by RESOLVE_NO_XDEV'
else
    echo 'SKIP/UNPROVEN mount crossing: environment cannot construct bind-mount fixture'
fi
