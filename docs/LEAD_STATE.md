# PolaCore Lead State

This file is a fallback repository copy of the state that should normally be maintained in the permanent GitHub issue `[Lead] PolaCore state & priorities`.

## Current phase

Security substrate / trusted launch path.

## Demonstrated baseline

- `engineering` contains runtime-confinement policy/configuration validation and Evil-test CI infrastructure.
- Configuration-level evidence must not be generalized to effective runtime guarantees.
- Bundle/root-path validation work exists, but validation-to-launch identity and full trusted-store promotion remain unresolved.

## Highest-value uncertainty

Safe bounded traversal and materialization of attacker-controlled staging into a trusted launch closure without path escape or substitution.

## Active objective

P117 `SourceTraversalCannotEscapeStaging`: run the bounded fd-relative/openat2 experiment described in `docs/NEXT_OBJECTIVE.md`.

## Next invariants after P117

P118 `CopyValidatedAgainstApprovedManifest`, P119 `CanonicalClosureNamespace`, P120 `CrashConsistentPromotion`.

## Deferred

CMS feature work, broad compatibility, user interface work, fs-verity hardening, and any promotion to `main`.
