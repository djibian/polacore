# Formal security constitution feasibility probe

Status: `HYPOTHESIS / EXPERIMENTAL`

Issue: #27

This directory tests one narrow question before PolaCore changes its long-term security ambition:

> Can a small, mechanically verified security kernel accept fully hostile caller inputs while preserving useful constitutional security properties without forcing formal verification across the whole CMS?

This is not production code and does not change the authoritative security invariant registry.

## Why this experiment exists

PolaCore already assumes that third-party component code can be fully compromised and already prefers explicit capabilities, narrow authority, fail-closed behavior, and a small trusted computing base. Formal verification is useful only if it strengthens that architecture without creating a larger or less understandable trust boundary.

The decisive integration risk is the boundary between verified and unverified code. A proof that relies on an unverified caller honoring a verifier-only precondition is not an acceptable PolaCore boundary. Therefore the two executable boundary functions in `constitution.rs` intentionally have no `requires` clauses and validate attacker-controlled request values internally.

## Model v0

The first model deliberately stays tiny. It represents:

- a constitutional allow/deny decision;
- a site-local allow/deny decision;
- an explicit capability presence bit;
- a capability epoch, modeling revocation/staleness;
- a minimal privileged state transition: acquiring administrator state.

It is intentionally not yet a complete capability system, identity model, secret service, plugin sandbox, or CMS authorization engine.

## Properties currently targeted

### C1 — Constitutional supremacy

If an operation is allowed, the constitution must allow it.

`final_allow -> constitution_allow`

A site policy can therefore restrict authority but cannot turn a constitutionally forbidden action into an allowed one.

### C2 — No authority without explicit current capability

An operation can be allowed only when an explicit capability is present and its epoch matches the current epoch.

This is a minimal model of revocation/staleness, not yet a proof that real capability objects are unforgeable.

### C3 — Complete mediation for the modeled admin transition

A transition from non-admin to admin can occur only after the boundary authorizer accepts the request.

The public experimental boundary takes arbitrary hostile inputs and has no caller precondition.

### C4 — State-integrity preservation

If the trusted state satisfies the modeled invariant before the transition, the mediated transition preserves it.

The first invariant is intentionally small: administrator state is never valid at epoch zero.

## What a successful Verus run means

A successful run means Verus mechanically discharged the stated proof obligations for this exact model and source revision, under the Verus toolchain's documented trusted assumptions.

It does **not** mean:

- PolaCore is formally verified;
- the operating system, compiler, solver, hardware, database, browser, Wasmtime, or cryptographic assumptions are proven;
- capabilities in a future runtime are already unforgeable;
- unverified code is prevented from bypassing a future Authority Core deployment;
- the model is complete or correctly captures every desired security property.

Those boundaries remain `UNPROVEN` until separately demonstrated.

## Proof-hygiene guard

`check_proof_hygiene.py` rejects known proof-shortcut mechanisms in this experiment source, including `assume`, `admit`, axioms, external verification bypasses, and assumed specifications. It also rejects a verifier-only `requires` clause at either marked untrusted-call boundary.

This guard is deliberately narrow and is not proof that no specification bug exists. Reviewer and Adversary inspection remain required.

## Initial TCB / assumption manifest

| Layer | Initial classification | Reason |
| --- | --- | --- |
| `constitution.rs` stated obligations | mechanically checked when Verus CI passes | exact experiment source |
| Rust/Verus boundary shape | structural + mechanically checked obligations | hostile request values are validated internally |
| proof-hygiene scanner | CI guard, not a theorem | detects selected shortcuts only |
| Verus verifier / `vstd` | trusted assumption | verifier implementation is outside this experiment's proof |
| SMT solver used by Verus | trusted assumption | solver correctness is outside this experiment |
| Rust compiler / LLVM for future executable deployment | trusted assumption | executable refinement is not yet demonstrated here |
| OS / process isolation / filesystem / database | `UNPROVEN` by this experiment | separate PolaCore invariants and runtime evidence |
| Wasmtime / WebAssembly | `UNPROVEN` by this experiment | possible defense-in-depth only |
| cryptographic hardness | conditional external assumption | requires algorithm agility rather than an eternal proof |

## Falsification plan

The next experiment increments should try to break the useful claim rather than enlarge the model automatically:

1. attempt privilege amplification through local policy;
2. attempt stale/replayed capability use;
3. model cross-component resource authority;
4. model a confused-deputy request;
5. replace booleans with capability objects/tokens and test whether construction authority can be made non-forgeable at the API boundary;
6. determine whether an unverified caller can bypass all privileged effects rather than merely call the verified authorizer correctly;
7. measure proof/TCB growth as the model gains one realistic CMS operation.

If useful properties require verification to spread across a large fraction of PolaCore, or if privileged effects remain bypassable outside the verified boundary, issue #27 must be classified `MODIFY` or `NO-GO` rather than weakening the constitution.

## Reproduction

CI pins a specific Verus weekly release instead of tracking a floating latest build. For the initial experiment the pin is:

`0.2026.08.15.7d4628a`

The official Verus installation documentation lists Ubuntu 24.04 x86_64 as a prebuilt supported platform. The binary release contains the verifier, `vstd`, and solver needed for command-line verification.

Run the hygiene guard first:

```sh
python3 experiments/formal-constitution/check_proof_hygiene.py
```

Then, with the pinned Verus release unpacked:

```sh
/path/to/verus-x86-linux/verus experiments/formal-constitution/constitution.rs
```

Until that exact verification succeeds in repository CI, all formal claims in this directory remain `UNPROVEN`.
