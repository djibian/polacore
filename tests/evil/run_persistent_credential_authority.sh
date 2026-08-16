#!/usr/bin/env bash
set -euo pipefail

src=${1:-tests/evil/persistent_credential_authority.c}
bin=$(mktemp)
trap 'rm -f "$bin"' EXIT

gcc -O2 -Wall -Wextra -Werror -o "$bin" "$src"

for mode in --filtered --exec-filtered; do
  out=$($bin "$mode")
  printf '%s\n' "$out"

  for probe in shmget msgget semget mq_open memfd_create socket add_key keyctl; do
    line=$(printf '%s\n' "$out" | grep -E "^${probe}[[:space:]]")
    printf '%s\n' "$line" | grep -q 'rc=-1 errno=1 (Operation not permitted)'
  done
done
