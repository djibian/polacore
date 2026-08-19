# P117 adversarial evidence for draft PR #2

## Scope

Issue #4 asks the Adversary to try to falsify the P117 candidate independently.
The probe in `tests/evil/p117_adversarial_probe.py` exercises the Linux x86-64
`openat2(2)` mechanism directly rather than importing the Experimenter's code.
It uses a stable `O_PATH` staging descriptor and
`RESOLVE_BENEATH | RESOLVE_NO_MAGICLINKS` (plus `RESOLVE_NO_XDEV` for the mount
case). The target is draft PR #2 and the functional/security objective is P117
`SourceTraversalCannotEscapeStaging`.

Exact reproduction command:

```sh
python3 tests/evil/p117_adversarial_probe.py
```

## Observed evidence

Environment: Linux x86-64, kernel `6.18.35`, container without usable bind-mount
authority.

* `REFUTED`: enumeration followed by a constrained open does **not** bind a name
  to the object the enumerator observed. A deterministic `os.replace` between
  `stat(..., follow_symlinks=False)` and `openat2` caused the constrained open to
  read the attacker's replacement ordinary file. Both objects were below the
  stable root, so this is not a staging escape. It refutes any stronger
  object/path-substitution conclusion and shows that the candidate primitive
  cannot by itself establish P118 manifest identity.
* `PROVEN_BY_TEST`: swapping the observed name to an absolute symlink outside
  staging was rejected (`EXDEV`). A `/proc/self/fd/0`-style path was also
  rejected (`EXDEV`). This evidence is about these deterministic cases, not all
  race schedules or all magic-link mount topologies.
* `REFUTED`: resolution flags do not reject special objects. `openat2` returned
  an `O_PATH` descriptor for an attacker-created FIFO. A traversal/materializer
  therefore needs an explicit type allowlist before any blocking or
  side-effecting open. Device-node behavior was not exercised because creating
  device nodes would require authority not available to an untrusted staging
  producer in this environment.
* `UNPROVEN`: mount crossing. The bind-mount setup was denied. This run neither
  validates `RESOLVE_NO_XDEV` against a real crossing nor tests a crossing that
  appears concurrently after enumeration.

## Assessment of draft PR #2 evidence

The candidate's narrow escape-resistance evidence remains valid for the tested
ordinary symlink and proc-style absolute magic-link paths. It must be **narrowed**:
safe resolution of a supplied name does not demonstrate safe recursive
enumeration/materialization composition, stable object identity, or rejection
of special objects. Mount-crossing behavior remains `UNPROVEN` in this
environment. No result here proves complete P117 traversal, and no result should
be reported as P118 evidence.

## Limitations and non-goals

The probe does not modify production code, implement a materializer, or claim
exhaustive race coverage. It does not exercise bind mounts, device nodes, UNIX
sockets, recursive rename storms, filesystem notification interactions, or
filesystem-specific aliasing. Those remain `UNPROVEN`, not PASS. The probe adds
no trusted-computing-base component.
