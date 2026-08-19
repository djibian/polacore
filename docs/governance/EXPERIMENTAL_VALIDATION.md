# PolaCore Experimental Validation Doctrine

## Role of PolaCore

PolaCore is the experimental laboratory for engineering mechanisms, security properties, agent workflows, CI oracles, and development practices that may later be adopted by production-oriented projects such as WebeeBlocks.

PolaCore is allowed to explore, fail, refute assumptions, compare alternatives, and retain negative results. WebeeBlocks must not be used as the first place to discover whether a cross-project engineering mechanism is sound.

This doctrine does not turn PolaCore into a generic dumping ground: experiments must still be relevant, bounded, reproducible, and connected to an explicit question.

## One-way promotion rule

Cross-project transfer is one-way by default:

`PolaCore experiment -> independent falsification/review -> validated reusable pattern -> WebeeBlocks adoption`

WebeeBlocks may report requirements, constraints, failures, or candidate questions back to PolaCore, but those reports are inputs to experiments, not evidence that a proposed mechanism is valid.

No experimental PolaCore result is automatically authorized for WebeeBlocks.

## Validation classes

Use the evidence vocabulary from `AGENTS.md`. For cross-project promotion, a candidate must have:

1. an explicit claim and scope;
2. reproducible evidence appropriate to the claim;
3. independent Verification/Reviewer scrutiny;
4. Adversary scrutiny when the claim concerns security, trust boundaries, races, authority, hostile input, isolation, or other high-cost failure modes;
5. no unresolved blocking contradiction;
6. remaining uncertainty stated explicitly;
7. a retained artifact, test, document, or implementation that another project can inspect.

A candidate is **PROMOTABLE** only when the Lead records that the evidence supports reuse within a stated scope. `INFERENCE`, `HYPOTHESIS`, `UNPROVEN`, `REFUTED`, misleading SKIP, or merely green CI are never promotable.

## Promotion record

Every reusable result intended for another project must have a promotion record containing:

- candidate/pattern name;
- originating issue/PR and exact validated commit or retained artifact;
- claim being promoted;
- evidence classification;
- tests/review/adversarial evidence;
- assumptions and environmental limits;
- known counterexamples or rejected alternatives;
- permitted reuse scope;
- explicit remaining uncertainty;
- Lead decision: `PROMOTABLE` or `NOT_PROMOTABLE`.

Promotion records should live under `docs/governance/promotions/` when they become necessary. Do not create speculative records for ideas that have not reached validation.

## Adaptive agent pipeline

The Lead selects the smallest process that can produce trustworthy evidence.

### Normal
`Lead -> Builder -> Verification`

Use for bounded low-risk work whose mechanism is already validated.

### Experimental
`Lead -> Experimenter -> Builder -> Verification`

Use when behavior, architecture, measurement, or causality is uncertain.

### High-risk / security
`Lead -> Experimenter -> Adversary -> Reviewer -> Builder -> Verification`

Use for security invariants, trust boundaries, authority, confinement, races, hostile input, persistence, or similarly costly false claims.

Roles are epistemic functions, not ceremony. A role may be skipped only when its information value is genuinely unnecessary.

## Independence

Whenever practical, the agent/model that verifies or attacks a claim should be independent from the agent/model that implemented it. GitHub-native automated review may act as Reviewer-0, but it is a filter, not final evidence.

## GitHub as shared memory

Experiments, contradictions, decisions, promotion records, and remaining uncertainty must be written to GitHub. Chat history is not authoritative project state.

## Relationship with WebeeBlocks

PolaCore validates reusable engineering doctrine and mechanisms. WebeeBlocks integrates only the subset that has crossed the promotion gate and is relevant to its product needs.

PolaCore must not dictate WebeeBlocks product requirements, pedagogy, UX, or domain behavior. Those remain WebeeBlocks concerns. The laboratory validates *how* we engineer and prove mechanisms; the product decides *what* it needs.
