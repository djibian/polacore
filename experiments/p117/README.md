# P117 bounded source-traversal experiment

This is isolated experimental evidence, not production traversal or promotion code.
It addresses P117, `SourceTraversalCannotEscapeStaging`, and no P118-P120 claim.

## Hypothesis

`HYPOTHESIS`: opening an attacker-controlled staging directory once with
`O_PATH|O_DIRECTORY|O_CLOEXEC`, then opening source paths relative to that stable
file descriptor with Linux `openat2(2)` and

```text
RESOLVE_BENEATH | RESOLVE_NO_MAGICLINKS | RESOLVE_NO_SYMLINKS | RESOLVE_NO_XDEV
```

prevents a read from resolving outside the staging directory for the exercised
lexical, symlink, magiclink, ancestor-substitution, and symlink-swap attacks.
Symlinks are objects to be handled as data by a future traversal; this experiment
intentionally proves only that they are never followed for reads.

## Minimal setup and discriminating result

`openat2_beneath.c` creates a private staging directory and an adjacent file with
the unique content `OUTSIDE_SECRET`. It first demonstrates an ordinary bounded
read. It then attempts `..`, an absolute pathname, a symlink to the adjacent file,
a `/proc/self/fd/N` magiclink, replacement of the pathname by which the already
open staging directory was reached, and 20,000 opens while a child swaps a regular
file and an escaping symlink.

The hypothesis is refuted if any attack opens outside content. It is supported for
an exercised attack only if the valid control read succeeds and the attack either
fails resolution or yields no outside content. Errnos are printed rather than
assumed. The runner also tries to construct a bind mount below staging; inability
to do so is printed as `UNPROVEN`, never `PASS`.

## Exact reproduction

From the repository root:

```sh
./experiments/p117/run.sh
```

Equivalent compilation of the main probe:

```sh
cc -std=c11 -Wall -Wextra -Werror -O2 \
  experiments/p117/openat2_beneath.c -o /tmp/p117-openat2
/tmp/p117-openat2
```

The runner exits 77 with `UNPROVEN` if `openat2` is unavailable. Any observed
outside read or unexpected child failure exits nonzero. A mount fixture, when the
environment permits `mount --bind`, is checked with:

```sh
/tmp/p117-openat2 --mount-probe ROOT_CONTAINING_MOUNTPOINT
```

where the mounted file is `ROOT_CONTAINING_MOUNTPOINT/mounted/secret`.

## Observed result and environment

Observed on 2026-08-19 in the Codex container:

```text
Linux 6.18.35 x86_64
Ubuntu 24.04.4 LTS
cc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0
PASS valid fd-relative read flags=0xf
PASS dotdot denied errno=18 (Invalid cross-device link)
PASS absolute denied errno=18 (Invalid cross-device link)
PASS symlink denied errno=40 (Too many levels of symbolic links)
PASS proc-magiclink denied errno=40 (Too many levels of symbolic links)
PASS ancestor rename retained original root object
PASS symlink-swap race outside_reads=0 inside_reads=3619 denied=16381
RESULT PROVEN_BY_TEST exercised attacks could not escape staging
UNPROVEN mount crossing: environment cannot create a bind mount (CAP_SYS_ADMIN unavailable)
```

Race counts are scheduling-dependent; the security discriminator is
`outside_reads=0`, not the exact opened/denied counts.

## Evidence and conclusion

- `PROVEN_BY_TEST`: on the recorded kernel, the valid control and the lexical
  `..`, absolute, symlink, proc-magiclink, stable-root ancestor replacement, and
  one 20,000-iteration symlink-swap run genuinely exercised `openat2`; none read
  the adjacent secret.
- `UNPROVEN`: mount crossing in this container, because it lacks authority to
  create the required bind mount.
- `INFERENCE`: the flag set is a suitable minimal candidate for later Builder
  work, provided supported kernels are established and independent adversarial
  review does not find a counterexample. This experiment is not production code.
- P117 as a universal claim remains `UNPROVEN`. A finite race run cannot prove
  absence of every interleaving, and this probe does not enumerate a directory,
  preserve symlinks as data, reject every special object, test concurrent mount
  injection, test hostile network/FUSE filesystems, or cover kernel-version
  differences. It also does not address copying, manifest binding, hardlinks,
  metadata, or trusted publication (P118-P120).
