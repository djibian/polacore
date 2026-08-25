# PolaCore A0 Autonomous Maintenance

## Purpose

A0 maintenance reduces owner relay work for routine agent-infrastructure failures while keeping security, authority, and architecture decisions human-governed.

A0 is operational repair only. It is not a product-development authority and it is not a security-design authority.

## Control model

The autonomous loop is deliberately split:

1. a read-only classifier decides whether observed failure evidence fits the narrow A0 repair surface;
2. a path-bounded Maintainer may propose a patch but has no GitHub-write authority;
3. a separate publisher reapplies the patch to a clean `engineering` checkout;
4. a deterministic gate validates the exact diff before a PR is opened and again on the PR head;
5. existing exact-SHA CI/contracts must pass;
6. an independent read-only Reviewer may block but never authorizes merge;
7. only the deterministic A0 gate may merge an accepted A0 PR into `engineering`;
8. a successful merge may rearm the source task for a completely fresh run.

Model output is always `INFERENCE`. A0 merge eligibility is a deterministic policy decision.

## Autonomous repair surface

A0 v1 intentionally permits only three repair shapes.

### 1. Albert model replacement

One already-allowlisted Albert model identifier may be replaced one-for-one by another already-allowlisted model identifier in existing operational workflow/config/agent files.

Allowlisted identifiers:

- `albert/deepseek-v4-flash`
- `albert/qwen3-coder-30b-A3b-instruct`
- `albert/openai/gpt-oss-120b`

No provider URL, API-key mapping, permission, command structure, action reference, trigger, or secret wiring may change autonomously.

### 2. Bounded timeout increase

An existing `timeout-minutes:` value may only increase, never decrease, and may never exceed 20 minutes.

### 3. Proven Python bytecode ignore rules

A0 may add only these already-demonstrated ignore rules to `.gitignore`:

- `__pycache__/`
- `*.py[cod]`

It may never remove ignore rules.

## Explicitly excluded from A0

The following always require escalation rather than autonomous merge:

- `main`, promotion rules, branch protections, or rulesets;
- `AGENTS.md`;
- `docs/security/**`, security invariants, architecture, or product policy;
- product source or product tests;
- A0 classifier/Maintainer/Reviewer profiles;
- A0 validator, deterministic patch gate, A0 workflows, or this policy document;
- permission changes, GitHub-token authority, secret references, provider endpoints, or credential handling;
- changes to validators that interpret model output;
- arbitrary shell/workflow logic changes;
- package/tool version changes;
- new files, deleted files, renames, or large refactors;
- any failure whose smallest trustworthy repair is not one of the three A0 shapes above.

## Fail-closed requirements

A0 must stop instead of guessing when:

- classification confidence is below the A0 threshold;
- the repair changes an unallowlisted path;
- the diff cannot be represented as exact safe replacements;
- candidate CI is absent, skipped where evidence is required, failing, or stale;
- the independent Reviewer returns a blocking or ambiguous verdict;
- the source task has exhausted its bounded repair budget;
- the exact PR head SHA has changed after validation;
- GitHub refuses the merge under repository protections.

## Retry budget

The first proving loop is issue #36. At most three successful A0 repair merges may rearm #36. After that, another failure is escalated and remains fail-closed.

A failed A0 proposal does not silently consume a retry and does not rearm the task.

## Evidence vocabulary

- classifier and Reviewer conclusions: `INFERENCE`;
- deterministic patch-shape acceptance: `VERIFIED_BY_CI` only for the explicit gate checks;
- candidate workflow/test results: `VERIFIED_BY_CI` only for those exact checks and SHA;
- inability to run a required check: `UNPROVEN`, never PASS;
- A0 auto-merge: integration mechanics only, never proof of product correctness or security.

## Human boundary

A0 is designed to make the owner **human-on-the-loop** rather than a mechanical relay. The owner remains the authority for security/architecture choices, promotion to `main`, and any change outside the narrow deterministic A0 surface.