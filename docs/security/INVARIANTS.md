# PolaCore Security Invariant Registry

## Purpose

This is the authoritative repository registry for PolaCore security invariants. It replaces the practice of keeping the only durable copy of invariants inside recurring-task prompts.

The historical architecture work defines invariants P37 through P121. Migration of the full historical wording into this file is intentionally incremental: no historical invariant is considered removed merely because its full text has not yet been migrated here.

## Status vocabulary

- `ACTIVE`: required by the current architecture.
- `CANDIDATE`: under evaluation.
- `SUPERSEDED`: replaced by a stronger or clearer invariant; replacement must be identified.
- `REFUTED`: the proposed property or mechanism was shown invalid.

Evidence is classified using the vocabulary in `AGENTS.md`.

---

## Historical registry migration

### P37–P111

Status: `ACTIVE / MIGRATION_PENDING`

These invariants were developed during the initial Architecture / Engineering / Red Team loop. They remain part of the security baseline until individually migrated, superseded, or explicitly retired with evidence.

The Lead role must progressively migrate them when they become relevant to active work rather than bulk-copying stale prompt state without validation.

---

## P112 — FreshInodePromotion

Status: `ACTIVE`

### Claim

Trusted launch artifacts are materialized onto fresh trusted inodes rather than treating attacker-controlled staging inodes as trusted merely after validation.

### Threat

Retained writable handles, hardlinks, aliases, or later mutation of staging objects could otherwise modify an artifact after approval.

### Required evidence

Reproducible tests must demonstrate that post-promotion mutation authority retained over the source cannot mutate the trusted copy.

---

## P113 — NoExternalInodeAliases

Status: `ACTIVE`

### Claim

A trusted launch artifact must not retain untrusted external aliases that can mutate or substitute its materialized objects.

### Required evidence

Adversarial tests for source hardlinks, retained descriptors, and aliasing must fail closed or demonstrate isolation of the trusted materialization.

---

## P114 — NoPrePublicationWritableHandleLeak

Status: `ACTIVE`

### Claim

Before a trusted artifact is published as authoritative, no untrusted actor retains a writable handle capable of changing the published closure.

---

## P115 — ContentDigestCoversClosureSemantics

Status: `ACTIVE`

### Claim

Artifact identity must cover the security-relevant semantics of the complete closure, not merely a subset of file bytes.

### Threat

Modes, symlink targets, canonical paths, metadata, or closure structure may change execution semantics without changing an incomplete digest model.

---

## P116 — PublishIsCreateOnly

Status: `ACTIVE`

### Claim

Publication into the trusted launch store is create-only and must not silently replace an existing authoritative object.

### Candidate mechanism

`renameat2(..., RENAME_NOREPLACE)` or a demonstrably equivalent primitive.

---

## P117 — SourceTraversalCannotEscapeStaging

Status: `ACTIVE`

### Claim

All reads from untrusted staging are bounded to a stable staging root and cannot be redirected outside it during traversal.

### Baseline direction

- stable staging root descriptor;
- descriptor-relative resolution;
- `openat2` constraints such as `RESOLVE_IN_ROOT` or `RESOLVE_BENEATH`, `RESOLVE_NO_MAGICLINKS`, and appropriate no-crossing/no-symlink policy;
- symlinks treated as data rather than traversal instructions;
- rejection of unexpected special objects and path escapes.

### Required adversarial evidence

Test at least symlink to host data, symlink-swap race, ancestor rename, magiclink, mount crossing where testable, and path escape attempts.

---

## P118 — CopyValidatedAgainstApprovedManifest

Status: `ACTIVE`

### Claim

Fresh trusted materialization is verified against an already approved identity/manifest. Copying data from staging does not itself make the data trusted.

### Required semantics

Where applicable the approved identity covers canonical path, object type, size/content digest, executable mode, symlink target, and allowlisted metadata.

Mutation during copy must produce mismatch/failure, not a different accepted closure.

---

## P119 — CanonicalClosureNamespace

Status: `ACTIVE`

### Claim

Every path in an approved closure has one unambiguous canonical interpretation in the target filesystem namespace.

### Threats to reject or normalize explicitly

- `.` / `..` traversal;
- absolute paths;
- duplicate canonical paths;
- symlink-child ordering attacks;
- hardlink aliasing;
- special objects;
- archive extraction ambiguities;
- OCI whiteout/opaque semantics leaking into the final trusted closure;
- filesystem-specific collisions where relevant.

---

## P120 — CrashConsistentPromotion

Status: `ACTIVE`

### Claim

A crash during trusted artifact promotion cannot create an authoritative partially materialized closure or cause unfinished private staging to become trusted after restart.

### Baseline direction

Write/materialize, flush relevant file and directory state, close writable handles, revalidate approved closure, perform create-only publication, then persist the parent directory entry.

### Required evidence

Crash/fault injection around write, fsync, rename/publication, and parent-directory persistence; concurrent same-identity promotion must also be tested.

---

## P121 — VerityDoesNotReplaceClosureIdentity

Status: `ACTIVE`

### Claim

`fs-verity`, if used, is defense in depth for file-content integrity and does not replace trusted namespace, closure identity, metadata semantics, fresh-inode promotion, or create-only publication.

### Consequence

The baseline architecture does not depend on fs-verity to satisfy P112–P120.

---

## Registry maintenance rule

When evidence changes an invariant:

1. update this registry in the same PR or a directly linked documentation PR;
2. preserve the old conclusion in Git history and relevant issue discussion;
3. identify whether the change is `REFUTED`, `SUPERSEDED`, or a clarification;
4. update `docs/security/EVIDENCE.md` with the corresponding reproducible evidence.
