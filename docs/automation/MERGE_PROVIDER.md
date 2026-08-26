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

Ruleset `21296946` requires the GitHub Actions check
`deterministic-contract` and uses strict required-status semantics: a pull
request must be up to date with `engineering` before GitHub may merge it. The
bypass list remains empty.

The concurrent canary established the provider-enforced base transition:

- PR #58 head `e7139435f015ac089a4c812feb88385de6a3cf21` and PR #57
  head `fb692a464041c0d87cb16390c25ff7e51ec3406d` both passed the required
  check on base `e2b987dd0d42fd53143ae749d2726ecf3700cbeb` in runs
  `32938239022` and `32938237905`;
- merging #58 advanced `engineering` to
  `80c311568580ac8166c3d340da12d8402403be79`;
- #57 then became one commit behind and GitHub rejected the unchanged-head
  squash request with HTTP 405 because required check `deterministic-contract`
  was expected;
- updating #57 onto the new base produced exact head
  `0e22dd4ab1e92c3d3998acf72eddffde7ccf1930`, whose fresh required check
  passed in run `32938375757` before GitHub accepted the squash merge to
  `4cb1078daea67445f4713b15ba5a0c4db80cb8c8`.

This is bounded evidence that the current no-bypass strict ruleset prevents an
unchanged PR head which was tested on an older base from being merged after
`engineering` advances. It does not establish a durable journal or grant a
controller permission. The required workflow must run for every PR targeting
`engineering`; path-filtered required checks would deadlock unrelated product
changes.
