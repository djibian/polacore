# Merge certificate builder v1

## Purpose

The certificate builder turns bounded evidence claims into the canonical
certificate consumed by the Merge Governor. It is deterministic, offline and
non-authoritative: it has no token, network, subprocess, candidate execution,
publication or merge capability.

A certificate is not an approval. The Governor accepts it only when a separate
authenticated GitHub observation corroborates every candidate-bound field and
all other eligibility rules remain true.

## Separation of inputs

| Input | Trust | May define |
| --- | --- | --- |
| Governor policy from exact `engineering` | trusted | repository, integration branch, assurance floors, forbidden paths |
| task manifest from exact `engineering` | trusted | issue, PR, assurance, authorized paths, acceptance commands, required evidence identities |
| certificate claims | untrusted | proposed base/head, Git changes, run/job facts and conclusions |

Claims deliberately cannot contain task authority, assurance or policy fields.
Unknown fields fail closed. The builder copies those authority-bearing values
only from the trusted policy and manifest.

## Evidence binding

Checks and verdicts must match the manifest exactly. Each certificate entry is
bound to:

- semantic check name/kind or verdict role;
- exact workflow name and repository path;
- exact trusted base SHA used as workflow code;
- exact candidate head SHA;
- positive GitHub run and job IDs;
- `PASS` or independent `NON_BLOCKING` outcome.

Checks and verdicts cannot reuse a job. Missing, extra, duplicated, stale or
renamed evidence is rejected. Including the workflow path closes the remaining
same-name workflow ambiguity in the original certificate schema.

## Static authority checks

Before emitting a certificate, the builder also rejects forks, `main`, unknown
agent branch namespaces, identical base/head SHAs, paths outside task authority,
forbidden control-plane paths, non-regular Git modes, assurance below a path
floor and `OBJECTIVE_AMENDMENT`.

These checks are defense in depth. GitHub state is not trusted merely because it
appears in claims: the observation collector must independently reconstruct the
diff and resolve the exact workflow runs/jobs, reviews, threads, base and head.
The Governor then requires certificate/observation equality.

## Remaining boundary

This lot does not fetch GitHub, execute checks, validate model output, store an
artifact, hold merge authority, perform compare-and-swap or write the post-merge
audit record. Those capabilities remain separate and `UNPROVEN` until later
issue #48 lots.

Run the combined contract with:

```text
python3 -m unittest -v \
  tests/test_merge_governor.py \
  tests/test_merge_observation_collect.py \
  tests/test_merge_certificate_build.py
```
