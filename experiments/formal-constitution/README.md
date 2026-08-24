# Formal security constitution feasibility probe

Status: `HYPOTHESIS / EXPERIMENTAL`

Issue: #27 — draft PR #28

This directory tests one narrow question before PolaCore changes its long-term security ambition:

> Can a small, mechanically verified security kernel accept hostile requests while preserving useful constitutional security properties without forcing formal verification across the whole CMS?

This is not production code and does not change the authoritative P37-P121 security-invariant registry.

## Current result

The experiment has produced an important positive **and** negative result.

### v0 — mechanically verified, security model insufficient

`constitution.rs` verifies successfully, but its useful security claim was falsified during review: constitutional permission and capability facts were themselves caller-supplied. A hostile caller could therefore assert `constitution=true` and suitable capability values.

This is intentionally retained as a counterexample showing that:

> A valid proof of a weak or incorrectly trusted specification does not establish the desired security property.

The v0 model is **not** a candidate PolaCore authorization boundary.

### v1 — trusted authority state, hostile request only

`capability_kernel.rs` moves the authority roots into opaque private `KernelState`:

- constitutional decision;
- local site-policy decision;
- issued grant presence and identifier;
- grant subject, resource and action;
- grant epoch and current revocation epoch.

The hostile caller supplies only a `Request` containing:

- caller identity;
- claimed capability identifier;
- resource;
- action.

`authorize_request` has no Verus `requires` clause and guarantees that its executable result equals an opaque authorization predicate derived from trusted kernel state.

On exact PR-head commit `f05df03a73fc608f90a1d07853b07a6305f283dc`, CI reported:

- v1 model: **8 verified, 0 errors**;
- deliberately broken v1 with subject binding removed: **7 verified, 1 error** and rejection as required;
- proof-hygiene scanner: passed for three named hostile boundaries;
- exact checked-out SHA: matched the PR head;
- Verus archive SHA-256: matched the repository-pinned digest.

This evidence is meaningful but still narrow. It verifies the stated v1 model, not PolaCore as a whole.

## Candidate properties demonstrated in the v1 model

The current model mechanically supports these narrow statements over its trusted state and request semantics:

1. **Constitutional denial cannot be amplified by local policy.**
2. **A forged capability identifier is denied.**
3. **A capability cannot be reused by a different subject.**
4. **A capability cannot be reused for a different resource.**
5. **A capability cannot be reused for a different action.**
6. **A stale grant epoch is denied.**
7. **The executable boundary result refines the opaque authorization predicate.**

The model does **not** yet prove whole-system complete mediation: an equivalent privileged effect could still exist outside this modeled boundary in a future implementation. That is now the decisive feasibility question.

## Why the unverified/verified boundary matters

A proof that relies on an unverified caller honoring a verifier-only precondition is not an acceptable PolaCore security boundary. For that reason, named hostile entry points are checked by CI to ensure they have no `requires` clause.

The v0 failure exposed a second rule: hostile callers must not supply authority facts merely because the verifier can reason about them. Authority roots must come from state controlled by the trusted kernel.

## Proof-hygiene guard

`check_proof_hygiene.py` scans all Rust/Verus sources in this experiment and rejects selected proof-shortcut mechanisms, including:

- `assume`;
- `admit`;
- axioms;
- `external_body` / verifier-external bypasses;
- `assume_specification`.

It also binds checks to the actual named hostile boundary functions rather than movable comment markers and rejects verifier-only `requires` clauses on them.

This is a CI guard, not a theorem that the specification is correct. Independent Adversary/Reviewer inspection remains mandatory.

## Toolchain pinning and remaining supply-chain assumption

The experiment currently pins:

- Verus: `0.2026.08.15.7d4628a`;
- Verus x86 Linux ZIP SHA-256: `0467d3dd832e29d301abdd83d60237f0299d0a0acba3041388af066c8b31d1e4`;
- Rust toolchain required by that Verus build: `1.97.1-x86_64-unknown-linux-gnu`;
- GitHub runner family: Ubuntu 24.04;
- `actions/checkout` by commit SHA.

The Verus digest was established once from the upstream release download and is now checked on every run. This prevents unnoticed later substitution under the same release URL, but the initial digest observation remains a **trust-on-first-use assumption**, not independently authenticated provenance.

## TCB / assumption manifest

| Layer | Current classification | Notes |
| --- | --- | --- |
| v1 stated Verus obligations | `FORMALLY_VERIFIED` for exact passing revision | only the stated model/code obligations |
| v1 opaque trusted-state boundary | formal + structural experiment evidence | hostile request cannot directly set private authority fields through the modeled API |
| v0 useful authority claim | `REFUTED` as sufficient model | retained as a proof/specification counterexample |
| proof-hygiene scanner | CI guard | detects selected proof shortcuts/preconditions, not all specification defects |
| Verus / `vstd` / SMT solver | trusted assumption | verifier and solver are outside the proof |
| Rust compiler / LLVM for deployed executable | trusted assumption / future work | executable deployment and compiler refinement are not proved end-to-end |
| initial Verus archive provenance | conditional TOFU assumption | subsequent byte substitution is detected by pinned SHA-256 |
| OS / process isolation / filesystem / database | `UNPROVEN` by this experiment | must be supported by separate runtime/structural evidence |
| whole-system privileged-effect mediation | `UNPROVEN` | decisive next experiment |
| Wasmtime / WebAssembly | `UNPROVEN` here | possible defense-in-depth, not part of current theorem |
| cryptographic hardness | conditional external assumption | requires crypto-agility rather than an eternal theorem |

## Constitutional governance lesson

Formal verification does not protect PolaCore if an agent can silently weaken the specification and then prove the weakened version. The experimental `CONSTITUTION_DRAFT.md` therefore treats the machine-readable constitution as a separate root of trust:

- ordinary implementation work must not silently amend it;
- weakening a constitutional property must be an explicit constitutional amendment;
- the old/new property, newly admitted threat and proof impact must be visible;
- independent adversarial review and owner approval are required;
- proof failure blocks the formal claim rather than justifying specification weakening.

This governance rule is especially important if future AI agents become much more capable than today's agents.

## Decisive next feasibility gate

The next experiment should stop proving more Boolean authorization facts and test the architectural boundary itself:

> Can a realistic privileged PolaCore effect be made unreachable to untrusted code except through the small verified Authority Core?

A useful next slice should include one concrete CMS operation, for example a publication/admin state change or a brokered sensitive-data operation, and demonstrate:

1. the untrusted worker lacks direct database/filesystem/secret authority for that effect;
2. the only exposed route is a narrow request protocol;
3. trusted state constructs/looks up grants rather than trusting caller-supplied grant facts;
4. the verified kernel decides the operation;
5. a deliberately malicious worker cannot achieve the same effect through a second path;
6. adding this realistic effect does not cause proof obligations to spread through a large fraction of the CMS.

If this cannot be achieved, the constitution + small verified kernel hypothesis should be classified `MODIFY` or `NO-GO`, not rescued by weakening the claim.

## Reproduction

CI verifies the exact PR-head SHA and refuses to execute a Verus archive whose digest differs from the repository pin.

Locally, after obtaining the pinned Verus archive and required Rust toolchain:

```sh
python3 experiments/formal-constitution/check_proof_hygiene.py
/path/to/verus-x86-linux/verus experiments/formal-constitution/constitution.rs
/path/to/verus-x86-linux/verus experiments/formal-constitution/capability_kernel.rs
```

The current long-term PolaCore ambition remains unchanged until issue #27 reaches an explicit `GO / MODIFY / NO-GO` conclusion.
