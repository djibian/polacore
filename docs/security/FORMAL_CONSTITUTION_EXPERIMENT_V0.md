# Formal security constitution feasibility result

Date: 2026-08-25  
Issue: #27  
Pull request: #28  
Archived experiment head: `3066747b769b463f5456dfced06d7572fa3e420b`  
Exact-head workflow run: `32756156073`

## Decision

`MODIFY` — retain the constitution plus a very small verified Authority Core as a promising direction, but do not yet amend the long-term PolaCore security claim or promote the experimental code to production architecture.

PR #28 and its exact head remain the immutable code/diff archive. This document records the durable conclusion so the source branch can be deleted without losing the decision or evidence address.

## What the experiment established

The v0 Verus model mechanically discharged its stated obligations but was independently refuted as a useful hostile-boundary model: authority facts were caller supplied. This is a retained counterexample to the false implication “the proof verifies, therefore the intended security property holds.”

The later v1 model moved constitutional policy, site policy, grant identity/binding and revocation epoch into opaque trusted `KernelState`; the hostile caller supplies only a request. It added checks bound to named hostile entry points, exact-PR-head checkout, a pinned Verus archive digest and negative controls.

On exact head `3066747b769b463f5456dfced06d7572fa3e420b`, workflow run `32756156073` completed successfully. This is `VERIFIED_BY_CI` only for the stated v0/v1 formal obligations, hygiene checks, negative controls and pinned inputs used by that run.

The v1 model supports narrow statements including constitutional-denial supremacy, forged capability-ID denial, subject/resource/action binding and stale-epoch denial within its modeled state.

## What remains unproven

- whole-system complete mediation of every privileged effect;
- inability of a compromised worker to reach an equivalent database, filesystem, secret or publication path outside the verified kernel;
- construction, persistence, concurrency, delegation and recovery semantics of real grants;
- compiler/refinement, verifier/solver, OS/runtime and cryptographic assumptions;
- authenticated provenance of the initial Verus digest beyond trust on first use;
- proof-maintenance cost across normal CMS evolution.

The exact-head CI occurred after the earlier independent review findings were addressed, but no new independent review of the final head establishes that all specification defects are exhausted. Green formal CI is therefore not an architectural `GO`.

## Highest-information successor

Model one realistic create-only trusted-publication transition and couple it to a runtime slice in which a compromised worker is denied every direct equivalent write path. Establish at least:

- `Published -> Authorized`;
- `Published -> requested identity == approved identity`;
- an existing authoritative identity is never replaced;
- denial or conflict leaves authoritative state unchanged;
- the trusted-state invariant is inductive;
- the verified Authority Core is the only reachable route to the effect.

If the effect remains bypassable or proof obligations spread through a large fraction of the CMS, classify the direction `MODIFY` or `NO-GO` rather than weakening the claim.
