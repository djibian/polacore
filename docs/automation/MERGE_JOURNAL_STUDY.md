# Merge Governor durable journal study

Issue: #48  
Parent program: #47  
Status: design study only; no live authority is introduced by this document.

## Question

The controller protocol already requires a durable monotone journal before it may issue a merge compare-and-swap. The missing property is a concrete store whose observable state can move only:

`ABSENT -> PREPARED -> COMPLETED`

for one exact `bundle_binding_sha256`, while surviving process restart and making ambiguous writes recoverable without issuing a second merge.

This study deliberately does **not** create a GitHub App, secret, new ruleset, protected journal branch, external service, provider endpoint, or live merge controller.

## Required properties

A candidate store must provide all of the following before it can be called a durable journal:

1. **Exact-key identity** — the primary key is the exact bundle binding digest; the payload repeats repository, PR, base SHA, head SHA, policy/certificate/observation/decision digests and merge method.
2. **Monotonicity** — `PREPARED` cannot return to `ABSENT`, be replaced by a different prepared payload, or be rewritten as another bundle. `COMPLETED` is terminal and immutable.
3. **Atomic transition** — readers observe either the old complete row or the new complete row, never a partially rewritten logical record.
4. **Crash recovery** — after process restart, a committed `PREPARED` or `COMPLETED` record can be read without relying on in-memory state.
5. **Fail closed on contradiction** — malformed schema, duplicate identity with different payload, impossible transition, or database error stops the controller.
6. **No merge authority** — the store implementation has no GitHub token, network client, merge API, candidate checkout, subprocess execution, or provider endpoint.
7. **Single-host scope is explicit** — a local database is not silently treated as a distributed consensus system or as protection against host compromise/rollback.

## Options considered

### Repository/Git branch journal

A dedicated protected Git ref could provide remote persistence and auditability, but it would require creating a new governed branch/ruleset and deciding who may update it. That is a new authority boundary explicitly outside the current authorization. It is therefore **not selected** in this lot.

### External database/service

A hosted database or key/value service could provide durable remote state, but it introduces credentials, endpoint trust, availability semantics and a new external authority. It is **not selected** without an explicit owner decision.

### Local SQLite journal

SQLite is available in the Python standard library and can provide transactional state without network or publication authority. It is the smallest testable candidate for the current offline phase.

The upstream SQLite documentation states that:

- transactions are atomic and SQLite's commit protocol uses filesystem synchronization to make committed state durable under the documented assumptions;
- in WAL mode, `PRAGMA synchronous=FULL` adds a WAL sync after each transaction commit and is documented as ACID;
- `synchronous=NORMAL` in WAL mode may lose the most recent committed transaction after OS/power failure, so it is insufficient for this journal's intended durability claim;
- durability ultimately depends on the VFS, filesystem and storage stack honoring synchronization requests, so power-loss durability must not be generalized beyond those assumptions.

Primary sources:

- SQLite, **Atomic Commit In SQLite**: https://www.sqlite.org/atomiccommit.html
- SQLite, **PRAGMA synchronous**: https://www.sqlite.org/pragma.html#pragma_synchronous
- SQLite, **Write-Ahead Logging**: https://www.sqlite.org/wal.html

## Proposed offline prototype contract

A future retained prototype may use a single local SQLite database with:

- `journal_mode=WAL`;
- `synchronous=FULL` verified on every opened connection;
- one table keyed by `bundle_binding_sha256`;
- canonical JSON payload stored together with individually indexed identity fields;
- `CHECK (state IN ('PREPARED','COMPLETED'))`;
- an insert-only `PREPARED` transaction;
- a guarded `UPDATE ... WHERE state='PREPARED' AND bundle_binding_sha256=?` for completion;
- a database trigger rejecting all `COMPLETED -> *` updates and all identity/payload changes;
- no delete path in the journal API;
- read-back validation through the existing `validate_journal()` before the controller trusts a row.

The application must treat `sqlite3.DatabaseError`, lock timeout, failed commit, unknown transition count, integrity-check failure, or read-back mismatch as `AdapterError`/`UNPROVEN`, never as success.

## Tests required before retention

The prototype is not accepted until deterministic offline tests demonstrate at least:

1. fresh prepare persists after closing and reopening the database;
2. replay of the exact prepare is idempotent;
3. a second prepare for the same binding with any changed identity/payload is rejected;
4. completion persists after reopen;
5. replay of the exact completion is idempotent;
6. `COMPLETED -> PREPARED`, `COMPLETED -> different COMPLETED`, delete, and identity mutation are rejected;
7. two connections racing to prepare the same exact key converge to one identical record or fail closed;
8. two connections racing with contradictory records cannot both commit;
9. a controller recovery run seeing durable `PREPARED` plus an already merged live state completes the record without a second merge request;
10. database corruption/open/transaction errors become explicit failure and never authorize merge.

A process-kill test can establish recovery after application crash. A true power-loss claim needs a suitable crash/power-cut harness and storage environment; ordinary unit tests cannot prove that property.

## Evidence boundary

This study is `VERIFIED_BY_PRIMARY_SOURCE` only for the cited SQLite semantics and `INFERENCE` for their suitability to the PolaCore single-host journal design. No concrete SQLite journal implementation has yet been retained or verified by CI in this lot.

Even after an offline prototype passes tests, the following remain `UNPROVEN` until separately established:

- durability under the actual production filesystem/storage/power-loss model;
- rollback resistance against a compromised host or restored filesystem snapshot;
- multi-host failover/consensus;
- placement and lifecycle of the journal database;
- the privileged GitHub merge adapter;
- the complete synthetic canary and fresh real-task acceptance path required by #48.

## Next smallest safe step

Implement the SQLite journal as a **storage-only** adapter behind the existing controller protocol and exercise the tests above. Keep the GitHub collector and merge action separate; do not give the journal network or publication authority.