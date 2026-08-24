# Constitution-to-PolaCore traceability — experimental

Status: `EXPERIMENTAL / ANALYSIS`

Issue: #27

Purpose: determine whether the proposed constitutional layer strengthens existing PolaCore work or would require a separate security architecture. This mapping is intentionally conservative: an architectural intention or policy check is not promoted to an end-to-end proof.

## Evidence classes used here

- `FORMAL-MODEL`: mechanically verified for the exact experiment model only.
- `STRUCTURAL-DIRECTION`: accepted architecture intends to make the violation unavailable by construction.
- `TEST-EVIDENCE`: adversarial/runtime evidence exists for exercised cases.
- `GAP`: material work is still required before a constitutional claim is defensible.

## Mapping

| Candidate constitution | Existing PolaCore alignment | Current evidence | Material gap before adoption |
| --- | --- | --- | --- |
| **C1 Complete mediation of privileged effects** | `docs/ARCHITECTURE.md` assigns high-value transitions to Authority Core/Broker; Standard v0 workers have no durable writable paths and no post-READY path opens/file creation | `STRUCTURAL-DIRECTION`; policy mutation tests | Prove the actual launcher/effective runtime leaves no equivalent privileged path; bind at least one real privileged effect to the verified core |
| **C2 Constitutional supremacy / no local-policy amplification** | Capability-oriented architecture already assumes platform APIs enforce authorization independently of extensions | v1 `FORMAL-MODEL` for constitutional denial | Define the real constitutional policy root and prove local/admin/plugin policy composition cannot widen it |
| **C3 Explicit authority / no ambient authority** | `ADR-0003` explicitly rejects installation-implies-authority and direct DB/fs/network/secret/admin/publication access; Standard v0 denies broad filesystem authority | `STRUCTURAL-DIRECTION`; selected persistence/syscall `TEST-EVIDENCE` | Demonstrate the effective runtime and broker API together; enumerate every ambient channel relevant to a worker |
| **C4 Subject/resource/action binding** | ADR requires narrow operation-scoped capabilities and mediated extension-to-extension access | v1 `FORMAL-MODEL`: forged id, cross-subject, cross-resource and cross-action use denied | Replace the single-grant model with the real grant representation/lookup and define delegation semantics, if any |
| **C5 Revoked/stale authority cannot create future effects** | ADR requires revocation where practical and no continuing authority after extension removal | v1 `FORMAL-MODEL` for epoch mismatch | Model actual grant lifecycle, persistence, concurrent requests, in-flight authorization and restart/recovery semantics |
| **C6 Trusted state invariants are inductive** | P112-P121 already express state/transition invariants for trusted-artifact materialization and publication | P117 has bounded traversal `TEST-EVIDENCE`; v0 has only a toy formal transition | Formalize one realistic Authority Core transition and show the invariant survives all modeled success/failure outcomes |
| **C7 Untrusted data cannot become authority by interpretation** | P112-P121 distinguish hostile staging from trusted materialization; migration/site-design rules keep imports declarative | Strong `STRUCTURAL-DIRECTION`; P117 exercised attack evidence | Connect validated/promotion state to the formal Authority Core; complete P118-P120 evidence; cover all executable/trusted promotion paths |
| **C8 Secret use does not imply secret observation** | security model lists secrets as protected assets; brokered service architecture naturally supports operation-over-secret APIs | `STRUCTURAL-DIRECTION` only | Define a secret-service capability interface, test worker exfiltration paths and decide whether selected non-disclosure needs formal non-interference or a narrower theorem |

## Key conclusion

The proposed constitution is **not a competing architecture**. Most of its laws are abstractions over commitments that PolaCore already made independently:

- small Authority Core;
- explicit capabilities;
- brokered privileged effects;
- no ambient worker authority;
- hostile third-party execution assumption;
- fresh trusted materialization rather than trust-by-validation;
- fail-closed evidence discipline.

Formal verification would add value principally at the **semantic decision/state-transition layer**, while existing and future runtime experiments establish that untrusted code cannot bypass that layer.

This division is the main feasibility insight:

```text
constitutional theorem
        |
        v
small verified Authority Core
        |
        v
narrow broker protocol
        |
        +---- structural/runtime evidence ----> no bypass
        |
        v
privileged effect
```

The constitutional claim is only as strong as both sides:

1. the formal theorem about the core; and
2. the runtime/structural evidence that every relevant effect is mediated by that core.

## Highest-information next experiment

Use **create-only trusted publication** as the first realistic transition because it already intersects P116 (`PublishIsCreateOnly`), P118 (`CopyValidatedAgainstApprovedManifest`) and C1/C6/C7.

The formal model should require, for an attempted publication:

- trusted constitutional/site/capability state;
- subject/resource/action binding;
- current (non-stale) grant;
- an approved artifact identity/manifest digest;
- an empty target identity (create-only);

and should establish at least:

- `Published -> Authorized`;
- `Published -> requested_identity == approved_identity`;
- existing authoritative identity is never replaced;
- denied or conflicting publication leaves authoritative state unchanged;
- the trusted-state invariant is inductive.

A separate runtime slice must then try to achieve the same authoritative write directly from a compromised worker. If that direct path remains reachable, C1 is `REFUTED` for that architecture regardless of how strong the Verus proof is.

## Adoption decision implication

A `GO` for a formal constitution should require evidence that the two proof styles remain **composable without merging their TCBs into the whole CMS**:

- formal proof remains local to the small Authority Core;
- runtime confinement/broker evidence can evolve independently;
- the interface between them is narrow, versioned and reviewable;
- normal CMS features do not need to become formally verified merely to preserve constitutional security.
