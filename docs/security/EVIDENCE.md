# PolaCore Security Evidence Index

## Purpose

This file indexes reproducible security evidence. It is not a prose assertion ledger: entries should point to tests, commits, CI runs, experiments, or primary sources.

## Evidence classes

Use the classifications defined in `AGENTS.md`:

- `PROVEN_BY_TEST`
- `VERIFIED_BY_CI`
- `VERIFIED_BY_PRIMARY_SOURCE`
- `VERIFIED_BY_CODE_INSPECTION`
- `INFERENCE`
- `HYPOTHESIS`
- `UNPROVEN`
- `REFUTED`
- `FALSE_POSITIVE`

## Current repository evidence

### Runtime confinement policy / OCI configuration

Repository artifacts currently include:

- `security/lint_runtime_config.py`
- `security/runtime-confinement-profile-v0.json`
- concrete OCI-style fixtures under `tests/fixtures/oci/`
- adversarial runtime-confinement tests under `tests/evil/`
- `.github/workflows/security-evil-tests.yml`

Classification: configuration and policy properties may be `VERIFIED_BY_CI` when the relevant tests are green, but this does **not** by itself establish effective runtime confinement.

### Concrete bundle and rootfs validation

Historical engineering work added checks around concrete bundle layout, root-path containment, symlink rejection, and root filesystem identity evidence.

Classification: retain as repository/CI evidence for bundle validation, not as proof of validation-to-launch object binding.

### Validation-to-launch TOCTOU

Historical work identified path-based reopen/substitution after validation as a major remaining risk. Stable object identity or another demonstrable binding mechanism remains required before treating pathname validation as launch integrity.

Classification: `UNPROVEN` for full validation-to-launch binding unless newer repository evidence demonstrates otherwise.

### Privileged mount / object-capability experiments

Historical architecture records a probe involving Linux mount-object primitives that could not exercise the privileged path in ordinary CI because required capabilities were unavailable.

Classification: explicit `SKIP / UNPROVEN` until a privileged environment produces a real PASS or FAIL.

## Evidence entry template

When adding evidence, use:

```text
### <Invariant or claim>

Claim:
Classification:
Repository path/test:
Commit/PR:
CI run:
Environment:
Observed result:
Limits / remaining uncertainty:
```

## Rule

Do not duplicate large logs here. Link or identify the reproducible artifact and state exactly what it proves and what it does not prove.
