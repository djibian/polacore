# Merge Governor v1 contract

## Status and boundary

This is the deterministic, read-only decision core for issue #48. It does not
hold a GitHub token, call GitHub, run candidate acceptance commands, publish, or
merge. Adding the core does **not** establish unattended merge authority.

A future minimal controller may act on `ELIGIBLE` only when it:

1. checks out the Governor and policy from the protected `engineering` base;
2. builds the observation from authenticated GitHub state rather than PR text;
3. supplies a certificate for the unchanged pull-request head SHA;
4. receives `ELIGIBLE` from the trusted-base Governor;
5. re-reads the same head, base and mergeability immediately before requesting
   a protection-respecting squash merge into `engineering`;
6. records the merge result and certificate digest on the source issue.

Candidate-controlled workflow code must never be the Governor that judges that
candidate. The privileged controller must never check out or execute candidate
code while it holds publication or merge authority.

## Inputs

The core consumes three strict JSON objects:

- a trusted policy loaded from `config/merge_governor_policy_v1.json` on the
  protected base;
- an evidence certificate produced for one PR head;
- a trusted observation assembled from GitHub, the trusted task contract, exact
  check runs and independently validated verdicts.

All objects reject duplicate or unknown keys. The certificate and observation
must agree byte-for-data on every candidate-bound field. Policy is bound by both
version and canonical SHA-256 digest.

## Fail-closed rules

The core returns `UNPROVEN` unless all of these are true:

- repository and base are exactly `djibian/polacore` and `engineering`;
- the base is still the current `engineering` SHA;
- the exact PR head—not GitHub's synthetic merge commit—is certified;
- the head is an in-repository authorized agent branch;
- task issue, authorized paths and acceptance commands match trusted control;
- every Git change is an explicitly inventoried regular blob addition,
  modification or deletion on an authorized path outside forbidden
  authority/policy paths; renames, copies, symlinks and submodules fail closed;
- deterministic path floors do not exceed the declared assurance;
- every acceptance command maps to a named exact-head `PASS` check;
- every check and verdict was produced by workflow code bound to the trusted
  base SHA, never by the candidate version of its own judge;
- the assurance-required check kinds and independent non-blocking roles exist;
- no required evidence is missing, skipped, stale, contradictory, or ambiguous;
- no review conversation remains unresolved;
- the PR is non-draft, GitHub reports it mergeable, and no protection bypass is
  requested;
- the candidate does not change `main`, workflows, agent authority, product
  objectives, security constitution, Governor policy/code, or other v1-forbidden
  control-plane paths.

`OBJECTIVE_AMENDMENT` is never autonomous. The conservative v1 prohibition on
all workflow and agent-profile changes is intentional; a later semantic policy
may narrow that restriction only through separately governed evidence.

## Assurance profiles

- `STANDARD`: deterministic `TEST` evidence and independent `REVIEWER` verdict.
- `REINFORCED`: `TEST` and `SECURITY` evidence plus independent `LAB`,
  `ADVERSARY`, and `REVIEWER` verdicts.
- `CONSTITUTIONAL`: `TEST`, `SECURITY`, and `FORMAL` evidence plus independent
  `LAB`, `ADVERSARY`, and `REVIEWER` verdicts.

Security implementation, adversarial-test and experiment paths deterministically
raise the minimum to `REINFORCED`. Model inference may add assurance but cannot
lower these floors.

## Decisions

- `ELIGIBLE`: the supplied state satisfies the decision contract. It is still
  not a product-correctness or security proof.
- `ALREADY_MERGED`: the exact recorded certificate/head/merge tuple was already
  applied; the controller must make no second merge request.
- `UNPROVEN`: stop. No merge may be attempted.

Run the contract suite with:

```text
python3 -m unittest -v tests/test_merge_governor.py
```

The suite covers the positive STANDARD case and adversarial stale SHA, stale
policy, unauthorized path, self-gate modification, missing/SKIP evidence,
blocking review, `main`, fork, permission/workflow, constitution, assurance
downgrade, contradictory evidence, unresolved review and replay cases.
