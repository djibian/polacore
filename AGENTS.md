# PolaCore Agent Instructions

## Mission

PolaCore is an experimental secure CMS and component platform.

Its primary security objective is that a fully compromised third-party component must not be able to:

- create, promote, or impersonate an administrator;
- publish content without explicit authority;
- inject trusted or admin JavaScript;
- read secrets, trusted code, or unauthorized data;
- compromise another component;
- inherit user or administrator authority;
- obtain ambient database, filesystem, IPC, or network authority;
- escape its execution confinement;
- establish unauthorized persistence.

Security claims are not accepted because an architecture looks safe. They require reproducible evidence, primary-source support, or explicit reasoning whose assumptions are identified.

## Repository governance

Repository: `djibian/polacore`.

### `main`

`main` is protected. Never commit directly to `main`. Never merge or retarget a pull request to `main`. Only Emmanuel may explicitly authorize promotion to `main`.

### `engineering`

`engineering` is the integration branch for experimental development, retained prototypes, security tests, and CI evidence. Normal implementation pull requests target `engineering`.

### Working branches

Use short-lived branches:

- `codex/experiment/<issue>-<slug>`
- `codex/impl/<issue>-<slug>`
- `codex/attack/<issue>-<slug>`
- `codex/test/<issue>-<slug>`

Do not mix unrelated objectives in one branch or pull request.

## GitHub is the shared memory

Do not rely on chat history as project state.

Before starting work, read:

1. this `AGENTS.md`;
2. `[Lead] PolaCore state & priorities`;
3. the GitHub issue assigned to the work;
4. relevant architecture and security documents;
5. related PRs and review comments;
6. current CI evidence.

Important conclusions must be written back to GitHub. Do not encode project history in agent prompts when it can live in the repository.

## Evidence vocabulary

Use these terms consistently:

- `PROVEN_BY_TEST`
- `VERIFIED_BY_CI`
- `VERIFIED_BY_PRIMARY_SOURCE`
- `VERIFIED_BY_CODE_INSPECTION`
- `INFERENCE`
- `HYPOTHESIS`
- `UNPROVEN`
- `REFUTED`
- `FALSE_POSITIVE`

A green CI status is not automatically proof of the security claim. A skipped test is not a pass. A textual statement that an attack was attempted is not evidence unless the experiment is reproducible.

## Engineering principles

Prefer, in this order:

1. demonstrated behavior over assumed behavior;
2. causal fixes over workarounds;
3. small reversible changes over redesigns;
4. simple mechanisms over abstract elegance;
5. existing kernel/runtime guarantees over bespoke privileged code when the guarantees are equivalent and demonstrable;
6. narrow authority over ambient authority;
7. explicit capability transfer over implicit identity-based authority;
8. fail-closed behavior over recovery by assumption;
9. reproducible tests over prose security claims;
10. reduction of trusted computing base when security properties remain demonstrable.

Do not add complexity for hypothetical future requirements. Do not remove a defense unless the relevant invariant remains demonstrably satisfied.

## Security invariants

The authoritative invariant registry is `docs/security/INVARIANTS.md`.

When working on an invariant:

- identify it explicitly in the issue and PR;
- state the threat it prevents;
- state what evidence demonstrates it;
- state what remains unproven.

Never silently weaken an invariant to make an implementation pass. If implementation evidence contradicts an architectural assumption, report the contradiction instead of coding around it.

## Third-party component model

Assume a third-party component may achieve arbitrary code execution inside its assigned worker. Security must not depend on the component voluntarily obeying APIs or policies.

Treat component input, packages, archives, manifests, files, generated code, metadata, IPC messages, network responses, and migration content as attacker-controlled unless explicitly established otherwise.

## Authority model

Avoid ambient authority. A worker receives only the minimum authority required for the current operation.

Ephemeral UID/GID identity is not itself a durable security boundary. No persistent authority may depend solely on later reuse of an ephemeral UID/GID.

Persistent state and privileged operations must be mediated by trusted components using explicit authorization.

## Runtime confinement

Runtime security claims must be validated against effective runtime state where practical. Configuration text alone is insufficient evidence for claims involving namespaces, mounts, file descriptors, credentials, capabilities, seccomp, cgroups, systemd properties, network isolation, or process lifecycle.

Prefer tests that inspect the resulting process or kernel-visible state.

## File descriptors

Use an explicit FD allowlist. Unexpected descriptors are a security defect.

Do not pass directory FDs, arbitrary regular files, sockets, `O_PATH` handles, eventfds, or activation descriptors to untrusted workers unless an invariant explicitly requires and constrains them.

Tests involving EOF, EPIPE, shutdown, or process lifecycle must account for every duplicated endpoint.

## Filesystem and artifact handling

Untrusted pathname traversal must not escape attacker-controlled staging roots. Prefer descriptor-relative resolution and kernel-enforced path constraints.

Symlinks must be treated as data unless an explicitly documented policy requires following them. Reject unexpected special files, filesystem aliases, path escapes, ambiguous canonical paths, and authority-bearing metadata.

Trusted executable artifacts must be bound to verified content and closure semantics. Validation by pathname alone is not sufficient when an attacker can replace the resolved object before use.

## Tests

Every security-relevant fix should have the smallest test that would have failed before the fix. Prefer negative and adversarial tests where possible.

Tests must fail loudly when the property cannot actually be exercised. Never convert environmental inability to test into PASS. Use SKIP only when the limitation is explicit and visible in CI. Do not weaken assertions merely to make CI green.

## Experiments

Experimental code may intentionally test hypotheses. An experiment must state:

- hypothesis;
- minimal setup;
- expected discriminating result;
- observed result;
- environment;
- limitations.

Experimental success does not automatically authorize production architecture.

## Pull requests

Each pull request must identify:

- GitHub issue;
- security invariant or functional objective;
- scope;
- non-goals;
- tests executed;
- evidence produced;
- remaining uncertainty;
- trusted-computing-base impact if relevant.

Large unrelated refactors are not allowed inside security changes.

## Builder role

When acting as Builder:

- implement only work marked ready for build;
- keep the change minimal;
- add relevant tests;
- do not invent new architecture silently;
- report blockers or contradictions in the issue;
- never weaken tests or invariants to finish the task.

## Experimenter role

When acting as Experimenter:

- optimize for information gain, not production quality;
- create the smallest experiment that discriminates between hypotheses;
- record reproducible evidence;
- avoid expanding the production architecture;
- clearly distinguish experiment code from retained code.

## Adversary role

When acting as Adversary:

- assume the claimed property may be false;
- actively search for counterexamples;
- test boundary conditions, races, lifecycle failures, stale authority, confused-deputy behavior, injection, substitution, rollback, and persistence;
- prefer a failing reproducible test over a theoretical objection;
- do not modify product code merely to make an attack succeed.

## Reviewer role

When acting as Reviewer:

- do not assume green CI means the claim is proven;
- verify that tests exercise the stated property;
- look for ignored errors, permissive fallbacks, skipped paths, incomplete cleanup, TOCTOU windows, capability leakage, and unnecessary TCB growth;
- reject architectural scope creep hidden inside implementation changes;
- distinguish blocking defects from optional hardening.

## Stop conditions

Stop and report rather than guessing when:

- the requested change requires weakening a security invariant;
- the issue is architecturally ambiguous;
- primary evidence contradicts the requested implementation;
- credentials or secrets are required;
- privileged infrastructure unavailable in CI prevents a required claim from being demonstrated;
- an action would affect `main`.

## Definition of done

Security-relevant work is done only when:

1. the issue acceptance criteria are met;
2. relevant positive tests pass;
3. required adversarial tests pass;
4. CI contains no unexplained failure or misleading skip;
5. review found no blocking contradiction;
6. produced evidence is recorded;
7. remaining uncertainty is explicit.
