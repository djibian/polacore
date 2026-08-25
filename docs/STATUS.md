# PolaCore status

Last consolidated: 2026-08-25.

## Demonstrated baseline

- `AGENTS.md` is the agent constitution and `docs/security/INVARIANTS.md` is the authoritative invariant registry.
- `engineering` contains retained runtime-confinement tests, P117 experiments, adversarial evidence and independent review.
- Narrow descriptor-relative P117 containment is `PROVEN_BY_TEST` only for the exercised cases. Complete traversal, privileged mount crossing and P118-P120 remain `UNPROVEN`.
- The first real end-to-end GitHub agent task produced PR #46 and was integrated at exact merge SHA `d2c47d7dd053df3f460636c15b8eeaa2bc93ee6a` after deterministic tests and independent read-only review.
- The formal-constitution experiment demonstrated that a mechanically valid proof may still prove an insufficient model. Its improved trusted-state v1 is promising, but whole-system mediation remains `UNPROVEN`; see `docs/security/FORMAL_CONSTITUTION_EXPERIMENT_V0.md`.

## Active program

Issue #47 owns the autonomous, goal-adaptive GitHub development platform. Issue #48 is the first control-plane workstream: a deterministic Merge Governor that binds every decision to an unchanged candidate SHA and may integrate only into `engineering`.

The target roles are Lead, Lab, Engineering and Verification. Assurance is selected per objective and change impact, with deterministic policy setting a floor that model inference may raise but never lower.

## Current product-security work

- issue #3: durable Lead state and priorities register;
- issue #4: durable security threat and attack register;
- issue #5: P117 remains open but its rejected PR #8 implementation is closed;
- issues #47/#48: current autonomous-platform program;
- `main`: no autonomous write, merge or retarget; promotion requires Emmanuel's explicit separate authorization.

## Transitional limitation

The repository still contains provenance-bearing pilot workflows from the canary, Real Task v1 and A0 stages. They are not the generalized platform: several are tied to completed issue #36. They must be retired only after #48 and the reusable replacement preserve their tested authority boundaries and failure discriminators.
