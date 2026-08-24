# PolaCore security constitution — experimental draft v0.1

Status: `CANDIDATE / EXPERIMENTAL`

Issue: #27

This document is deliberately **not** the authoritative PolaCore constitution. It tests whether a small set of stable, implementation-independent security laws can sit above the existing P37-P121 invariant registry without replacing it.

## 1. Four layers, not one giant proof

PolaCore should not mix long-lived security meaning with implementation mechanisms.

### Layer A — Constitutional properties

Small, stable semantic laws that should survive implementation changes.

Examples: privileged effects require authorization; local configuration cannot override a constitutional denial; one component cannot inherit another component's authority.

### Layer B — Derived security invariants

Concrete obligations needed to realize the constitutional properties in a particular subsystem or design.

The existing P37-P121 registry belongs primarily here. For example, trusted-launch-store properties about fresh inodes, aliasing, traversal, closure identity and crash-consistent promotion are concrete obligations supporting broader trust-boundary and state-integrity laws.

### Layer C — Mechanisms

Replaceable implementation choices such as Rust types, Verus, Cedar, Linux primitives, systemd, WebAssembly/Wasmtime, PostgreSQL, cryptographic libraries, or a particular IPC protocol.

A mechanism is never constitutional merely because it currently works.

### Layer D — Evidence

Machine proofs, adversarial tests, CI evidence, code inspection and explicit assumptions supporting Layers A-C.

The evidence vocabulary remains the one defined in `AGENTS.md`.

## 2. Candidate constitutional properties

The notation below expresses intent, not yet a complete formal semantics.

### C1 — Complete mediation of privileged effects

**Law:** every security-sensitive effect must be caused through an authoritative mediation decision.

Conceptually:

`PrivilegedEffect(e) -> exists d: AuthorizedDecision(d, e)`

The security claim is invalid if an equivalent effect can be reached through an unmediated database, filesystem, network, process, secret, administrative, publication or internal-API path.

**Expected evidence class:** formal proof inside the Authority Core **plus** structural/runtime evidence that no privileged bypass exists outside it.

**Important:** proving one authorizer function is insufficient to prove C1 for the whole CMS.

### C2 — Constitutional supremacy / no policy amplification

**Law:** configurable site, tenant, plugin or feature policy may restrict constitutional authority but may not enlarge it.

`Allow_final -> Allow_constitution`

Equivalent conceptual composition:

`Allow_final = Constitution ∩ LocalPolicy ∩ ExplicitAuthority`

A local administrator can configure what the constitution permits, but configuration cannot turn a constitutionally forbidden action into a permitted action.

**Expected evidence class:** strong formal proof target.

### C3 — Explicit authority; no ambient authority

**Law:** possession of execution, installation, identity, code location, process membership or plugin status does not itself confer privileged authority.

`EffectiveAuthority(component) ⊆ ExplicitGrants(component)`

No third-party component gains database, filesystem, network, secret, publication, administrator or unrelated-component authority merely because it runs.

**Expected evidence class:** formal authorization/broker properties plus structural isolation.

### C4 — Authority is bound to subject, resource and action

**Law:** a grant for one subject/resource/action cannot be used as authority for another unless an explicit, constitutionally valid delegation rule says so.

For a successful request `r` using grant `g`:

`subject(r)=subject(g) ∧ resource(r)∈scope(g) ∧ action(r)∈actions(g)`

This is the core cross-component and confused-deputy protection law.

**Expected evidence class:** strong formal proof target, with explicit delegation semantics if delegation is ever introduced.

### C5 — Revoked or stale authority cannot create future effects

**Law:** a disabled/revoked/expired authority cannot be replayed to obtain a new privileged effect.

A minimal epoch formulation is:

`epoch(grant) != current_epoch -> Deny`

Real revocation will require stronger lifecycle semantics than a single epoch counter.

**Expected evidence class:** formal state-transition proof plus runtime/persistence evidence.

### C6 — Security invariants are inductive over trusted state transitions

**Law:** every accepted Authority Core state transition preserves the declared global security invariants.

`Invariant(S) ∧ AcceptedTransition(S,S') -> Invariant(S')`

Crash/recovery semantics must eventually be part of the transition model for invariants whose truth spans durable state.

**Expected evidence class:** strong formal proof target, supplemented by storage/crash evidence where the model meets external systems.

### C7 — Untrusted data cannot become authority by interpretation

**Law:** attacker-controlled content, metadata, manifests, imports, migration data, paths, templates, AI-generated output or IPC payloads do not acquire code/authority semantics merely through parsing or placement.

Conceptually:

`UntrustedData(x) -> no Authority(x) without an explicit trusted promotion transition`

This law connects directly to PolaCore's existing trusted-artifact and migration work.

**Expected evidence class:** formal promotion-state invariants plus structural parsing/type/confinement guarantees and adversarial tests.

### C8 — Secrets are exposed only by explicitly authorized disclosure semantics

**Law:** using a secret for an authorized operation does not imply authority to read or export the secret itself.

Prefer operations such as `sign(data)` or `send_with_credential(request)` over `read_secret()` when disclosure is unnecessary.

`CanUseSecretOperation(c) !-> CanObserveSecret(c)`

**Expected evidence class:** capability/interface proof plus process/runtime isolation; stronger non-interference proofs may be investigated for especially valuable secrets.

## 3. Properties intentionally not stated as absolute constitutional theorems yet

### Availability / resource exhaustion

CPU, memory, storage and network budgets are security-relevant, but their end-to-end guarantees cross schedulers, kernels, storage and external services. Treat resource limits as conditional/operational guarantees unless a narrower theorem is defined.

### Cryptographic hardness

PolaCore can prove that only an approved cryptographic service is invoked and that keys are not unnecessarily disclosed. It cannot prove forever that a cryptographic primitive remains computationally hard. Crypto-agility is therefore governance/architecture, not an eternal theorem.

### Browser/client security

PolaCore can constrain generated output and trusted/admin script boundaries, but the whole browser/platform ecosystem is outside the minimal formal TCB.

### Hardware and side channels

Any formal claim must state hardware, compiler, OS and side-channel assumptions explicitly rather than silently absorbing them into the word “secure”.

## 4. Constitutional governance requirements

Formal verification is insufficient if an AI or developer can silently weaken the specification and then prove the weakened program.

### G1 — Specification is a separate root of trust

The machine-readable constitution must be distinguishable from implementation/proof code. Ordinary Builder authority must not include silent constitutional edits.

### G2 — Constitutional amendments are explicit

Any change that weakens, removes or materially reinterprets a constitutional property must be labeled as a constitutional amendment rather than a normal implementation change.

An amendment must include:

- the exact old and new property;
- why the change is required;
- which threat becomes newly possible, if any;
- independent adversarial review;
- explicit owner approval;
- regenerated/rechecked proofs and derived-invariant impact.

### G3 — Proof continuity is release-gating

A release must not claim a formally protected property if the exact released Security Core revision lacks its required verification evidence.

Proof failure is a release failure, not an invitation to weaken the specification.

### G4 — Proof shortcuts are part of the TCB and must be visible

`assume`, axioms, unchecked/external bodies, assumed external specifications and equivalent constructs must either be forbidden in the protected core or enumerated as explicit trusted assumptions.

Automated agents must not be allowed to hide a failed proof by changing specifications, adding assumptions or replacing verified executable behavior with unverified behavior.

### G5 — The TCB is versioned and measurable

Each release claiming constitutional guarantees should publish a security manifest identifying at least:

- constitutional version;
- verified source revision;
- verifier/toolchain revision;
- verified properties;
- structural properties;
- conditional properties;
- external assumptions;
- explicit proof exceptions/assumptions;
- relevant TCB size or another stable measure of TCB growth.

A green CI badge alone is never the manifest.

## 5. Relationship to existing PolaCore security work

This proposal should **not** replace P37-P121.

A useful hierarchy is:

```text
Constitutional property Cx
        |
        +--> derived invariant Pn
        +--> derived invariant Pm
        |        |
        |        +--> mechanism / implementation
        |        +--> adversarial evidence
        |
        +--> formal proof obligation
        +--> structural/runtime boundary evidence
```

This means a concrete invariant can be refined or replaced as mechanisms evolve while the constitutional security meaning remains stable.

The current trusted-launch-store sequence P112-P121 is a good example: it should eventually be traceable upward to C1/C6/C7 rather than being promoted wholesale into the constitution.

## 6. Guarantee classes

Every user-visible security claim should identify its class.

| Class | Meaning |
| --- | --- |
| `FORMALLY_VERIFIED` | mechanically checked theorem for the exact stated model/code and explicit assumptions |
| `STRUCTURALLY_ENFORCED` | prevented by an architectural/type/isolation boundary but not fully formally proved end-to-end |
| `CONDITIONAL` | holds only if named external mechanisms/assumptions hold |
| `OPERATIONAL` | depends on deployment/configuration/process controls |
| `UNPROVEN` | desired property without sufficient current evidence |

These classes complement rather than replace the repository evidence vocabulary.

## 7. Feasibility gates before adoption

The constitution should remain experimental until issue #27 demonstrates all of the following:

1. multiple useful C-properties can be verified over a small executable or directly coupled kernel model;
2. a deliberately broken implementation fails verification;
3. an independent Adversary can challenge the specification without forcing it to be weakened;
4. real privileged effects can be architected so untrusted code cannot bypass the verified boundary;
5. capability construction/lookup/revocation can be modeled without trusting attacker-controlled grant state;
6. proof maintenance remains local as one realistic CMS operation is added;
7. constitutional specification changes can be distinguished and governed separately from ordinary implementation changes;
8. TCB assumptions remain small enough that the resulting claim is materially stronger than conventional testing alone.

Only after these gates should PolaCore consider adopting a formal constitution as an official product-security ambition.
