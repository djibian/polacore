# GitHub merge-provider capability gate v1

## Scope

`scripts/merge_provider_capability.py` is a pure, non-authorizing capability
assessment. It decides whether trusted primary-source evidence establishes all
provider and journal properties required by `MERGE_CONTROLLER.md`. It contains
no GitHub client, endpoint invocation, token, journal backend, publication or
merge capability.

Capability evidence is not self-authenticating. A future live component must
assemble it from authenticated GitHub state and primary documentation using
trusted-base code. Candidate content, PR text, labels and model output cannot
assert these facts or select an operation.

## Observation on 2026-08-25

The retained fixture `tests/fixtures/merge_provider_github_2026-08-25.json`
records the current evidence boundary:

- the synchronous and asynchronous pull-request merge APIs accept an exact
  expected PR head SHA, but document no expected base SHA precondition;
- the asynchronous result is retained for 24 hours, so it is not a durable,
  indefinite monotonic journal;
- a non-forced Git reference update enforces fast-forward behavior, not an
  exact PR/head/base/squash/audit transaction;
- a merge queue validates changes against the latest target state rather than
  the certificate's exact base, is not enabled by the current ruleset, and is
  documented for public organization-owned repositories while PolaCore is
  currently user-owned;
- ruleset `21296946` is active on `engineering`, requires a pull request,
  forbids deletion and non-fast-forward updates, and exposes no bypass actor.

Primary sources:

- [GitHub pull-request merge API](https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request)
- [GitHub Git-reference update API](https://docs.github.com/en/rest/git/refs#update-a-reference)
- [GitHub merge queue](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/incorporating-changes-from-a-pull-request/merging-a-pull-request-with-a-merge-queue)
- [GitHub ruleset rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- [Observed PolaCore engineering ruleset](https://api.github.com/repos/djibian/polacore/rulesets/21296946)

The resulting decision is `UNPROVEN`. In particular, a fresh read immediately
followed by `PUT /pulls/{number}/merge` must not be relabeled as atomic
base-and-head CAS.

## Eligibility contract

An operation is eligible only when primary evidence establishes all of these
properties without inference:

- available for this repository;
- exact PR, head SHA and base SHA preconditions in the write transaction;
- protection-respecting behavior without bypass;
- required squash method;
- exact merged-PR audit result;
- outcome recoverable from fresh authenticated state.

The journal must separately be available, bound to the exact bundle, durable,
indefinitely retained, inaccessible to the candidate, and monotonic from the
exact `PREPARED` record to the exact `COMPLETED` record only.

The evaluator computes these statuses from trusted-base operation, journal and
source registries; input evidence cannot strengthen a registered semantic fact
or provide an `ELIGIBLE` label. Adding a stronger provider operation requires a
separately reviewed trusted-code change. Unknown fields, unregistered or changed
sources, changed repository/target/method, duplicate identities and ambiguous
operation selection fail closed.

## Decision boundary

No current operation is selected and no live adapter may be installed from
this evidence. Resolving the gap may require a repository-governance change,
an organization/merge-queue model with recertification, or a separately proven
GitHub App and journal. Those choices affect rulesets, external authority or
the exact-base policy and therefore remain outside autonomous scope.

Run the complete offline contract with:

```text
python3 -m unittest -v \
  tests/test_merge_governor.py \
  tests/test_merge_observation_collect.py \
  tests/test_merge_certificate_build.py \
  tests/test_merge_decision_bundle.py \
  tests/test_merge_controller_protocol.py \
  tests/test_merge_provider_capability.py
```

## Governed strict-status experiment (2026-08-26)

Ruleset `21296946` now requires the GitHub Actions check
`deterministic-contract` and uses strict required-status semantics: a pull
request must be up to date with `engineering` before GitHub may merge it. The
bypass list remains empty.

This configuration statement is not evidence that the base race is closed. A
synthetic concurrent canary must first show that a second pull request which was
green on the old base becomes non-mergeable after the first pull request moves
`engineering`, and becomes eligible again only after its branch is updated and
the required check reruns. Until that observation is recorded on issue #48, the
provider operation remains `UNPROVEN`.
