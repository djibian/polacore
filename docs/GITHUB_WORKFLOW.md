# PolaCore GitHub Agent Workflow

## Shared-memory rule

GitHub is the shared state between ChatGPT governance, Codex workers, CI, and the human owner. Important conclusions must be written to issues, pull requests, or repository documentation.

## Permanent issues

Maintain two durable registers:

- `[Lead] PolaCore state & priorities`
- `[Security] PolaCore threat & attack log`

The Lead register tracks the current demonstrated baseline, highest-risk uncertainty, active objective, blockers, and deliberately deferred work.

The Security register tracks new attack classes, refuted assumptions, open security questions, evidence gaps, and high-value adversarial experiments.

## Work issues

Use one issue per bounded research question, experiment, implementation increment, or security decision.

Recommended structure:

- Goal
- Security invariant
- Why now
- Known evidence
- Unknown
- Acceptance criteria
- Required adversarial tests
- Non-goals
- Evidence produced

## Codex roles

### Experimenter

Runs the smallest discriminating experiment. Optimizes for information gain rather than production quality.

### Builder

Implements only an objective that governance has declared ready to build. Opens a focused PR to `engineering`.

### Adversary

Attempts to falsify the claimed property independently, preferably with reproducible failing tests or attack harnesses.

### Reviewer

Audits whether the PR and its evidence actually demonstrate the stated claim and whether TCB/complexity increased unnecessarily.

## Normal flow

1. Governance selects the highest-value uncertainty or smallest useful objective.
2. A GitHub work issue is created or updated.
3. If uncertainty is fundamental, Experimenter runs first.
4. Governance interprets the experiment and either rejects the direction or marks the issue ready for implementation.
5. Builder opens a focused PR to `engineering`.
6. Adversary attacks the PR independently.
7. Reviewer audits the claim and evidence independently.
8. GitHub Actions executes positive and Evil tests.
9. Builder corrects blocking findings without weakening invariants or tests.
10. Once evidence is sufficient, the PR may be merged to `engineering`.
11. Governance records the new demonstrated state and selects the next objective.

## `main`

No autonomous role may write, merge, or retarget to `main`. Promotion to `main` requires explicit authorization from Emmanuel.
