# Merge controller protocol v1

## Status and boundary

`scripts/merge_controller_protocol.py` is the deterministic state machine for a
future minimal controller. It verifies a complete decision bundle and drives an
injected interface, but this repository lot provides no GitHub client, token,
network call, subprocess, concrete journal, workflow permission, publication
capability or merge capability.

The interface is an obligation, not an authority grant. A live adapter remains
`UNPROVEN` until its semantics and permissions are separately established from
the protected `engineering` base. `MERGE_PROVIDER.md` defines the separate
primary-evidence capability gate that must succeed before such an adapter can
be selected.

## Atomicity requirement

The action method is `merge_squash_compare_and_swap`. It must atomically require
all of the following:

- repository `djibian/polacore`;
- target `engineering`;
- exact current `engineering` base SHA;
- exact unchanged PR head SHA;
- protection-respecting squash merge;
- no bypass, `main`, candidate execution or candidate-selected policy.

A fresh read followed by an ordinary merge request is not equivalent: the base
can move between those operations. A live GitHub adapter must not be installed
unless it can establish the exact base-and-head atomicity contract. If the
provider mechanism cannot do so, the state remains `UNPROVEN`; weakening the
base binding would require a separately governed authority/security decision.

## Durable journal and recovery

Before the single CAS attempt, the controller writes and rereads an exact
`PREPARED` journal entry bound to the bundle, certificate, observation, policy,
decision, base and head. No confirmed preparation means no merge attempt.
The live journal must be keyed by the bundle binding and monotonic: a confirmed
entry cannot disappear or be replaced, and only the exact transition from
`PREPARED` to `COMPLETED` is allowed.

After an observed merge, it writes and rereads `COMPLETED` with the exact merge
SHA and one honest completion kind:

- `CAS_CONFIRMED`: the CAS response and fresh merged state agree;
- `OBSERVED_AFTER_PREPARE`: a prepared intent existed and a retry observes the
  exact head merged, but the previous operation's response was uncertain.

The latter records recovery without falsely claiming which actor submitted the
merge. A merged PR without a matching durable prepared intent is `UNPROVEN` and
cannot be retroactively certified.

## Bounded behavior

One invocation issues at most one CAS attempt. It never loops on ambiguity.

- stale base, head or mergeability: `STOP_STALE`;
- uncertain operation with the PR still open: `RETRY_REQUIRED` for a later
  reconciler pass;
- applied response not corroborated by a fresh merged state:
  `MERGE_OUTCOME_UNCONFIRMED`;
- observed merge whose completion record is not durable:
  `MERGED_RECORD_UNCONFIRMED`;
- exact completed journal or replay bundle: no second merge request.

Unknown fields, journal substitution, fork/main/bypass states, malformed adapter
results and conflicting merge SHAs fail closed.

## Remaining live obligations

The following are intentionally absent: authenticated snapshot acquisition,
provider-specific atomic adapter, trusted durable journal, least-privilege
workflow, permission grant, post-merge issue update and deployment. The pure
protocol can be tested before any of those authority-bearing changes.

Run the complete offline contract with:

```text
python3 -m unittest -v \
  tests/test_merge_governor.py \
  tests/test_merge_observation_collect.py \
  tests/test_merge_certificate_build.py \
  tests/test_merge_decision_bundle.py \
  tests/test_merge_controller_protocol.py
```
