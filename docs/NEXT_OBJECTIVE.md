# First bounded objective — P117 staging traversal

## Goal

Demonstrate a minimal Linux fd-relative source-traversal pattern that prevents reads from escaping an attacker-controlled staging root.

## Security invariant

P117 — `SourceTraversalCannotEscapeStaging`.

## Why now

The repository already validates runtime-policy/configuration structures, but the next architecture step requires safely materializing untrusted artifacts into a trusted launch closure. Path-based recursive traversal would introduce a high-value escape/TOCTOU boundary before P118-P120 can be meaningfully implemented.

## Known evidence

- Existing bundle validation rejects important root-path and symlink classes.
- Historical architecture work identified descriptor-relative traversal and `openat2` constraints as the preferred Pareto direction.
- Full source traversal and trusted fresh-inode promotion are not yet demonstrated in the repository.

## Unknown

- minimal safe `openat2`/fd-relative flag combination for the supported Linux baseline;
- behavior for symlink-as-data versus followed paths;
- practical handling of mount crossings and kernel/environment differences;
- which race cases can be made deterministic enough for CI.

## Acceptance criteria

- [ ] A small isolated experiment exists and is reproducible.
- [ ] The traversal starts from a stable root descriptor and does not trust caller-controlled absolute paths.
- [ ] Attempts involving `..`, absolute paths, symlink escape, magiclink escape, and ancestor/path substitution are exercised where applicable.
- [ ] Any environment limitation is surfaced as explicit SKIP/UNPROVEN, not PASS.
- [ ] The experiment records exact kernel primitives/flags and observed errno/behavior.
- [ ] The result states whether the primitive is suitable for later Builder implementation and what remains unproven.

## Required adversarial tests

- [ ] symlink from staging to host data;
- [ ] magiclink attempt such as `/proc`-style resolution when applicable;
- [ ] parent/ancestor rename or substitution during traversal;
- [ ] lexical `..` / absolute escape;
- [ ] mount crossing when the test environment can exercise it.

## Non-goals

- full trusted launch-store implementation;
- P118 manifest approval;
- P119 full archive canonicalization;
- P120 crash-consistent publication;
- systemd launcher selection.
