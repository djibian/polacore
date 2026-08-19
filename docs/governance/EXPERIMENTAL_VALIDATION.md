# PolaCore Organizational Experimentation Doctrine

## Purpose

PolaCore is first and foremost its own secure CMS project. In parallel, its development process is used as a **testbed for organizational mechanisms**: agent roles, review structure, evidence discipline, issue/PR workflow, CI interpretation, escalation rules, independence between builder and verifier, and automation of the engineering loop.

The organizational objective is empirical: try a workflow on real PolaCore work, observe whether it improves rigor, autonomy, speed, causal diagnosis, review quality, and human intervention cost, then keep, modify, or reject it.

This document governs the organization of PolaCore only. It creates **no dependency, communication channel, promotion pipeline, shared backlog, shared state, or cross-project workflow with any other repository**.

## What may be experimented with

Examples include:

- Lead / Experimenter / Adversary / Reviewer / Builder / Verification role boundaries;
- adaptive pipelines depending on risk and uncertainty;
- GitHub as durable project memory;
- issue and PR contracts;
- evidence vocabularies;
- causal-bottleneck discipline;
- independent review and red-team passes;
- Copilot or other GitHub-native reviewer roles;
- automation of hand-offs and repetitive coordination;
- criteria for splitting or stopping a PR;
- rules limiting unnecessary human intervention.

These mechanisms are evaluated **because they are exercised on real PolaCore work**, not because they look elegant in documentation.

## No cross-project communication

PolaCore must not:

- receive requirements or tasks from another project as part of its normal workflow;
- send issues, PRs, artifacts, code, test results, or decisions to another project;
- maintain promotion records for another project;
- depend on another repository's state;
- coordinate agents across repository boundaries;
- treat another project as a consumer of PolaCore results.

Any later reuse of an organizational idea elsewhere is an external human decision made after observing PolaCore. It is not a PolaCore workflow and must not create coupling between repositories.

## How an organizational mechanism is considered validated

A mechanism is considered organizationally validated only after enough real use to judge its effects. The Lead should record, when useful:

1. the organizational problem being addressed;
2. the mechanism tried;
3. where it was exercised in PolaCore;
4. observed benefits and costs;
5. failure modes or unintended effects;
6. how much human intervention it required;
7. whether it improved or degraded evidence quality;
8. whether the mechanism should be kept, modified, or rejected.

A single successful PR is evidence, not necessarily validation. A mechanism that creates ceremony without information gain should be simplified or removed.

## Adaptive agent pipeline

The Lead selects the smallest process that can produce trustworthy evidence.

### Normal
`Lead -> Builder -> Verification`

Use for bounded low-risk work whose causal structure is understood.

### Experimental
`Lead -> Experimenter -> Builder -> Verification`

Use when behavior, architecture, measurement, or causality is uncertain.

### High-risk / security
`Lead -> Experimenter -> Adversary -> Reviewer -> Builder -> Verification`

Use for security invariants, trust boundaries, authority, confinement, races, hostile input, persistence, or similarly costly false claims.

Roles are epistemic functions, not ceremony. A role should exist only when it produces useful independent information.

## Independence

Whenever practical, the agent/model that verifies or attacks a claim should be independent from the agent/model that implemented it. GitHub-native automated review may act as Reviewer-0, but it is a filter, not final evidence.

## GitHub as shared memory

Experiments, contradictions, decisions, organizational lessons, and remaining uncertainty must be written to GitHub when they are important to future PolaCore work. Chat history is not authoritative project state.

## Human-intervention objective

The organization should progressively reduce the need for Emmanuel to relay messages mechanically between agents. Human intervention should concentrate on genuine decisions: objectives, product/security trade-offs, authorization boundaries, and ambiguous strategic choices.

Automation is successful only if it preserves or improves evidence quality while reducing coordination burden.

## Evaluation principle

PolaCore is the place where new organizational mechanisms are **tried before they are trusted**. The result of that experimentation is knowledge about how to organize AI-assisted engineering. Reuse of those organizational lessons elsewhere, if any, happens outside PolaCore and without technical or operational coupling.