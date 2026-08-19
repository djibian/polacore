# P117 narrow source-acquisition Builder evidence

Date: 2026-08-19  
Issue: #5  
Role: Builder  
Invariant: P117, `SourceTraversalCannotEscapeStaging`

## Scope

This increment retains a Linux-only primitive for acquiring one regular file
from an attacker-controlled staging root. It opens and retains an
`O_PATH | O_DIRECTORY | O_CLOEXEC` root descriptor, validates a pathname as a
nonempty sequence of canonical relative components, and calls `openat2(2)`
relative to that descriptor with:

```text
RESOLVE_BENEATH | RESOLVE_NO_MAGICLINKS | RESOLVE_NO_SYMLINKS | RESOLVE_NO_XDEV
```

Initialization probes that exact policy and fails closed if the syscall or
requested semantics are unavailable. Acquisition uses
`O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC`, inspects the resulting
descriptor with `fstat(2)`, and returns it only when it is a regular file. The
nonblocking open prevents an attacker-created FIFO from blocking before the
descriptor type check. No data is read by the primitive.

## Tests and evidence produced

Executed:

```sh
bash tests/evil/run_source_acquisition.sh
```

The deterministic harness reported `PROVEN_BY_TEST` for the exact exercised
lexical and absolute rejections, outside-symlink rejection, stable-root
ancestor replacement, post-acquisition in-root pathname substitution, and
FIFO/directory/socket rejection. In the substitution case, the data read came
from the already acquired and inspected descriptor, not from reopening its
pathname. This is descriptor-stability evidence only; it does not associate
that object with an earlier enumeration or approved manifest.

The environment could not construct the bind-mount fixture, so the runner
reported `SKIP/UNPROVEN` for mount crossing. The configured `RESOLVE_NO_XDEV`
bit is `VERIFIED_BY_CODE_INSPECTION`, not runtime proof in this environment.

## Non-goals and remaining uncertainty

Complete P117 remains `UNPROVEN`. This increment does not enumerate or recurse
through a directory tree and does not demonstrate descriptor anchoring during
recursive descent. Concurrently introduced mounts, other kernels and
filesystems, and hostile filesystem behavior remain untested. The allowlist is
intentionally limited to regular files; symlinks are rejected rather than
captured as data.

P118 object/manifest identity, P119 canonical closure namespace, P120
publication consistency, metadata policy, hardlink semantics, mutation during
copy, and the promotion backend are not implemented or claimed.

## Trusted-computing-base impact

The trusted code surface increases by one small Linux syscall wrapper,
canonical-component validator, descriptor lifecycle helper, and regular-file
type check. It adds no privileged process, daemon, parser, database, network
authority, recursive walker, or publication logic. The Linux kernel's
`openat2(2)` resolution enforcement and descriptor semantics are dependencies
of this narrow primitive.
