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

### Repository cleanup baseline

The 2026-08-25 repository-hygiene review was frozen at `engineering` SHA `d2c47d7dd053df3f460636c15b8eeaa2bc93ee6a` in issue #49. It recorded 36 branches, 29 pull requests, 16 active workflow files, 342 Actions runs and 86 tracked files before cleanup.

Classification: `VERIFIED_BY_CODE_INSPECTION` for that exact inventory snapshot. It is operational evidence, not a security proof.

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

### P117 descriptor-relative staging containment

Repository artifacts:

- `experiments/p117/`;
- `tests/evil/p117_adversarial_probe.py`;
- `docs/security/P117_ADVERSARIAL_EVIDENCE.md`;
- `docs/security/P117_REVIEW.md`.

The probe is executed directly with `python3 tests/evil/p117_adversarial_probe.py`. No retained Security Evil Tests workflow currently invokes it, so workflow run `32233103096` is not P117 execution evidence and must not be used as such.

Classification: narrow exact exercised containment cases are `PROVEN_BY_TEST`; enumeration-to-open object identity and implicit special-object rejection are `REFUTED`; privileged mount crossing and complete recursive materialization remain `UNPROVEN`.

Rejected implementation PR #8 is not evidence of a repaired primitive. Its remote head `8cfd78df2845b0c32e310bc41aa550bfc185f989` retained blocking root-anchor, special-object activation and FD-lifecycle defects.

### Formal security constitution feasibility

The durable result is `docs/security/FORMAL_CONSTITUTION_EXPERIMENT_V0.md`. PR #28 archives the exact experimental code at head `3066747b769b463f5456dfced06d7572fa3e420b`; workflow run `32756156073` completed on that exact head.

Classification: `VERIFIED_BY_CI` for the stated formal obligations and negative controls only. v0 adequacy is `REFUTED`; v1 is promising but whole-system complete mediation, unbypassability and production TCB remain `UNPROVEN`. Decision: `MODIFY`.

### First real autonomous task

Issue #36 produced PR #46, merged into `engineering` at `d2c47d7dd053df3f460636c15b8eeaa2bc93ee6a`. The generated invariant-listing tool passed its causal unit tests, deterministic candidate checks and an independent read-only Reviewer on the accepted exact candidate.

Classification: `VERIFIED_BY_CI` for the tested tool behavior and for one demonstrated end-to-end pilot path. It does not prove the generalized autonomous platform, which remains issue #47 work.

### Strict engineering base freshness

Claim: the active no-bypass ruleset prevents a PR tested on an older `engineering` base from merging after the base advances, and the required check is emitted for paths outside the former workflow filter.
Classification: `VERIFIED_BY_CI` for the exact workflow runs and `VERIFIED_BY_PRIMARY_SOURCE` for GitHub's observed ruleset rejection; not a proof of the future controller journal or whole Merge Governor.
Repository path/test: ruleset `21296946`; `.github/workflows/merge-governor-contract.yml`; concurrent PRs #57 and #58; global-trigger PR #60.
Commit/PR: old base `e2b987dd0d42fd53143ae749d2726ecf3700cbeb`; first merge `80c311568580ac8166c3d340da12d8402403be79`; updated #57 head `0e22dd4ab1e92c3d3998acf72eddffde7ccf1930`; second merge `4cb1078daea67445f4713b15ba5a0c4db80cb8c8`; global workflow change `6f47bf39a14c19934f1f9f0e294aa41b66d365d8`.
CI run: old-base runs `32938237905` and `32938239022`; updated-base run `32938375757`; global-trigger run recorded on PR #60.
Environment: GitHub-hosted `ubuntu-24.04`; GitHub repository ruleset with strict required status and empty bypass list.
Observed result: both concurrent PRs were initially green; after #58 advanced the base, GitHub rejected unchanged #57 with HTTP 405 and required a fresh `deterministic-contract`; after update and rerun, #57 merged. PR #60 changes only this previously unlisted path and therefore proves the required check is no longer path-filtered.
Limits / remaining uncertainty: no durable monotone journal, least-privilege live controller, privileged workflow, or fresh product-task auto-merge is established by this canary.

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
