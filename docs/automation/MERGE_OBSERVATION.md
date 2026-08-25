# Merge observation collector v1

## Purpose

The observation collector converts complete authenticated GitHub API snapshots
and a trusted-base task manifest into the strict observation consumed by the
Merge Governor. It is an offline deterministic normalizer, not a GitHub client.

It has no token, network, subprocess, candidate execution, publication, issue
write, pull-request write, or merge capability. A later trusted-base workflow
will fetch the API pages with read-only permissions and pass their bytes to this
collector.

## Trusted and untrusted inputs

- The Governor policy and task manifest must be checked out from the exact
  protected `engineering` base.
- The GitHub snapshot must be assembled by trusted workflow code from
  authenticated API responses, with every paginated collection explicitly
  marked complete.
- PR titles, bodies, comments, labels and approvals are not merge evidence.
- Candidate files are never executed by the collector.

The snapshot binds the open PR/base/head, current `engineering`, both exact commit
trees, the complete PR file page, workflow runs and jobs, reviews and review
threads. Unknown top-level keys and incomplete pages fail closed.

## Diff inventory

The collector independently compares the complete recursive base and head Git
trees and requires that result to equal GitHub's complete PR file inventory.
It preserves Git modes in the observation. Rename/copy normalization is forbidden;
symlink and submodule modes reach the Governor and are rejected there.

This closes omissions where a path list alone could hide a deleted trusted file,
rename, symbolic link, submodule or pagination truncation.

## Evidence identity

Required checks and verdicts come from the trusted task manifest. Evidence is
accepted only from exactly one successful job whose:

- workflow name and path match the manifest;
- event is `pull_request_target`, so workflow code comes from the base;
- workflow run head is the exact certified `engineering` base SHA;
- job name contains both `pr <number>` and the exact candidate head SHA;
- run and job are completed successfully;
- job ID is not reused by another check or verdict.

The trusted workflow must make a Reviewer/Adversary job succeed only after its
read-only model output has passed the deterministic verdict validator. A green
arbitrary candidate workflow is never evidence.

## Remaining boundary

This lot does not fetch live GitHub data, generate a certificate, hold merge
authority, support post-merge replay collection, or perform the final pre-merge
compare-and-swap. Those remain `UNPROVEN` until later #48 lots.

Run the combined contract with:

```text
python3 -m unittest -v tests/test_merge_governor.py tests/test_merge_observation_collect.py
```
