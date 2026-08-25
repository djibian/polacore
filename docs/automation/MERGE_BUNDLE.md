# Merge decision bundle v1

## Purpose and authority boundary

The offline bundle builder composes four deterministic artifacts for one exact
pull-request head: certificate, authenticated-state observation, Governor
decision and proposed intent. Each artifact has a canonical SHA-256 digest; a
fifth digest binds those digests together.

The bundle is evidence data, not merge authority. The builder and verifier have
no token, network, subprocess, candidate execution, publication or merge
capability. In particular, `PROPOSE_MERGE` is not an authorization and must
never be submitted directly to GitHub by untrusted code or model output.

## Construction and verification

`scripts/merge_decision_bundle.py`:

1. builds the certificate only from trusted policy/task authority plus bounded
   untrusted claims;
2. independently normalizes the complete authenticated GitHub snapshot;
3. asks the pure Governor to compare both views and decide;
4. derives an exact, non-authoritative intent from that decision;
5. binds all four canonical artifacts by digest; and
6. verifies the resulting bundle again before emitting it.

Unknown keys, stale policy, divergent claims and observation, moved
`engineering`, substituted artifacts, altered digests and malformed replay
records fail closed. A verifier reruns the Governor and reconstructs the intent;
recomputing a digest cannot turn an invalid decision into a valid one.

## Intent dispositions

- `PROPOSE_MERGE` is emitted only for `ELIGIBLE`. It binds repository, PR,
  `engineering`, base/head SHAs, squash method, policy, certificate and decision,
  directly binds the authenticated observation, and requires a fresh
  compare-and-swap.
- `NO_ACTION_ALREADY_MERGED` is emitted only for `ALREADY_MERGED`. It binds the
  exact recorded merge commit and forbids another merge request.
- `UNPROVEN` produces no intent or valid bundle.

The future privileged controller must load the verifier and policy from the
protected `engineering` base, verify the bundle, fetch fresh authenticated
GitHub state, compare the exact PR head and current base, respect branch
protection, and record the resulting merge tuple. It must not check out or
execute candidate code while holding write authority.

## Replay boundary

After a merge, replay requires a trusted record containing the original head,
the GitHub merge commit and exact certificate digest. The observation collector
requires that record to agree with GitHub before the Governor can return
`ALREADY_MERGED`. PR bodies, comments, labels and candidate artifacts are not a
trusted record source.

This lot deliberately does not define the live record store, GitHub permission
grant, privileged workflow or merge API adapter. Those authority-bearing
elements remain `UNPROVEN` and must be introduced separately without changing
this candidate's own judge to accept itself.

Run the complete offline contract with:

```text
python3 -m unittest -v \
  tests/test_merge_governor.py \
  tests/test_merge_observation_collect.py \
  tests/test_merge_certificate_build.py \
  tests/test_merge_decision_bundle.py
```
