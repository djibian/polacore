# Autonomous development model

## Purpose and sources of truth

PolaCore is developed by an autonomous GitHub-native system whose owner sets product objectives and performs only real-world tests or genuine product/constitutional decisions. GitHub issues, pull requests, exact commits, tests and versioned evidence are shared memory. Chat history and scheduled-task prompts are not authoritative project state.

Every actor reads `AGENTS.md`, the active issue, relevant product/security documents, the exact candidate diff and current CI evidence before acting.

## Branch authority

- `engineering` is the only autonomous integration target.
- `main` is reserved for explicit owner-authorized milestones. No autonomous actor may write, merge or retarget to it.
- Working branches are short-lived, issue-scoped and deleted after integration or recorded rejection.

## Cognitive roles

### Lead

Maintains the demonstrated product state, selects the smallest coherent high-value objective, assigns the assurance floor and prevents concurrent duplicate work.

### Lab

Runs the smallest discriminating experiment when causal, architectural, specification or environmental uncertainty would make direct implementation premature.

### Engineering

Implements the bounded accepted objective, adds causal tests and produces a candidate without holding publication or merge authority.

### Verification

Independently audits and attacks the exact candidate SHA. Reviewer and Adversary modes must reason from repository facts rather than private Builder reasoning.

Router, task runner, Publisher, Merge Governor, Reconciler and maintenance loops are mechanical control-plane services, not additional product roles.

## Adaptive assurance

The effective assurance level is at least:

```text
max(objective floor, change impact, dependency/invariant impact, uncertainty)
```

Model inference may raise this level but may never lower deterministic trusted policy. Missing, contradictory, stale or skipped evidence fails upward.

### STANDARD

Bounded functional work: deterministic causal tests, exact-SHA CI and independent review.

### REINFORCED

Data, permissions, integrations or meaningful trust impact: Lab where uncertainty exists, Engineering, Adversary and Reviewer.

### CONSTITUTIONAL

Authority kernel, broker, secrets, publication, capabilities, proof obligations or the control plane that judges/merges candidates: formal/model obligations where applicable, adversarial verification, trusted exact-SHA gates and explicit TCB accounting.

### OBJECTIVE_AMENDMENT

A change that weakens or replaces a product objective, security constitution or invariant. Agents may prepare evidence and a complete proposal but only Emmanuel may approve it.

## Normal state flow

1. Lead selects or refines one bounded issue and computes its assurance floor.
2. Lab resolves fundamental uncertainty when required.
3. Engineering produces a candidate branch/PR without publication authority.
4. Deterministic checks run on the exact candidate SHA.
5. Verification independently reviews and attacks that same SHA according to assurance.
6. The Builder may repair bounded causal findings; every head change invalidates prior candidate-bound evidence.
7. A trusted Merge Governor re-evaluates the immutable evidence certificate and may merge only the expected unchanged SHA into `engineering`.
8. Lead records the demonstrated state and selects the next objective.

## Authority separation

- untrusted/generated code and model output run without repository write, publication, merge or secret authority;
- a separate trusted Publisher may apply a validated patch to a clean trusted base;
- policy, validators and proof checkers used to judge a candidate are loaded from the trusted base, not from the candidate they judge;
- only the Merge Governor performs routine integration after deterministic policy accepts the exact SHA;
- public fork/PR content never receives secrets;
- permissions, secrets, provider endpoints, rulesets, branch governance and constitutional policy are outside autonomous repair surfaces unless the owner explicitly authorizes that exact change;
- a green job with a skipped required discriminator is not an acceptance certificate.

## Owner interaction

Routine issue transitions, branches, PRs, reviews, corrections and eligible merges into `engineering` do not require owner relay. Ask Emmanuel only for:

- a real-world or physical test that cannot be simulated;
- a genuine product objective or constitutional amendment;
- new external authority or credentials not already granted;
- promotion to `main`.

## Transitional pilots

Canary, Real Task v1 and A0 workflows are retained temporarily as evidence-bearing pilots. They do not define the target platform and must not be generalized by silently broadening permissions. Issue #47 owns replacement; issue #48 must establish the deterministic Merge Governor before obsolete generations are removed.
