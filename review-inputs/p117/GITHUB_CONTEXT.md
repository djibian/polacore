# P117 GitHub review packet

This file is a repository-local transport of GitHub context for Codex Reviewer tasks that cannot access the private repository metadata from inside Codex Cloud. It does not replace GitHub as the source of truth.

Snapshot date: 2026-08-19.

## Issue #3 — Lead state and priorities

Current milestone: Trusted Launch Store / anti-TOCTOU evidence before committing to a retained launch backend.

Demonstrated baseline:
- Security Evil Tests and runtime-confinement linting exist on `engineering`.
- The retained Experimenter artifact originally arrived as PR #2 and exercised a stable staging-root descriptor plus `openat2()` bounded resolution against lexical `..`, absolute paths, symlink, `/proc/self/fd` magiclink, ancestor replacement and a symlink-swap race without outside reads in the recorded Codex environment.
- The retained Adversary artifact originally arrived as PR #6 and independently confirmed that ordinary outside symlink and proc-style magic-link escapes are rejected in its exercised cases.

Adversarial findings:
- `REFUTED`: enumeration followed by a later constrained open does not bind the enumerated pathname to the same inode; an attacker can substitute another ordinary in-root object before open.
- `REFUTED`: `openat2` path-resolution flags alone do not reject special objects; an attacker-created FIFO was openable with `O_PATH`.
- `UNPROVEN`: mount crossing remains untested because the Codex container lacked bind-mount authority.

Current highest-risk uncertainty: the narrow `openat2` escape-resistance result survives, but complete P117 traversal is not established. The candidate must be composed with explicit object-type validation and a traversal/materialization design that does not confuse path containment with object identity.

Current objective: independent Reviewer audit before Builder work.

## Issue #4 — Security threat and attack log

Current attack focus: P117 `SourceTraversalCannotEscapeStaging`.

Confirmed/narrowed by adversarial work:
- Outside symlink escape and proc-style magic-link escape were rejected in the exercised cases: `PROVEN_BY_TEST` for those exact cases.
- Enumeration then open does not preserve object identity: `REFUTED` for any stronger claim that path containment alone binds the enumerated inode.
- Path-resolution flags do not reject special objects: `REFUTED`; attacker-created FIFO was openable with `O_PATH` and therefore requires explicit type policy.

Highest-value remaining attacks:
- mount crossing / bind-mount injection where privileges permit;
- full traversal/enumeration composition with descriptor-relative object inspection and later materialization;
- special objects beyond FIFO, hardlinks and metadata-bearing objects;
- rename/substitution races between enumeration, type validation, open and read;
- filesystem-specific/hostile semantics where reproducible;
- verify that future Builder code never turns in-root object substitution into approval bypass (P118 boundary).

Evidence gaps:
- no privileged mount-crossing result in Codex Cloud;
- no complete retained traversal/materializer implementation;
- no proof across all kernel/filesystem variants;
- P118-P120 remain intentionally unproven.

## Issue #5 — P117 work item

Goal: establish reproducible evidence for P117 before any production Builder implementation is accepted.

Security invariant: all reads from attacker-controlled staging must remain bounded to a stable staging root. Path traversal, symlink/magiclink resolution, ancestor replacement, mount crossing and race conditions must not cause host/outside bytes to be ingested.

Known evidence:
- Experimenter: stable `O_PATH` staging root plus `openat2()` with `RESOLVE_BENEATH | RESOLVE_NO_MAGICLINKS | RESOLVE_NO_SYMLINKS | RESOLVE_NO_XDEV`; exact exercised lexical `..`, absolute path, outside symlink, proc-style magiclink, ancestor rename and 20k symlink-swap cases produced no outside read in the recorded Codex environment.
- Adversary: independently confirmed outside symlink and proc-style magiclink rejection for exact cases, but `REFUTED` stronger assumptions that enumeration binds object identity and that path-resolution flags reject special objects; FIFO remained openable with `O_PATH`.

Unknown:
- privileged mount crossing;
- completeness under real directory enumeration/copy traversal;
- special objects/hardlinks/metadata interactions;
- broader race composition and filesystem/kernel variants;
- whether the candidate mechanism remains sound when integrated into retained code.

Acceptance criteria:
1. Independent Reviewer audits both retained experiment/adversary artifacts and their claim boundaries.
2. Environment-limited probes remain `UNPROVEN`.
3. Evidence is narrowed to a clearly stated mechanism/scope or refuted.
4. No Builder implementation starts until Lead explicitly marks the issue ready for build.

Non-goals: P118 manifest approval, P119 canonical namespace, P120 crash-consistent publication, production backend selection, or changes to `main`.

## Former PR #2 metadata

Title: `experiment(p117): add fd-relative openat2 probe to exercise staging-escape attacks`

Original head commit: `214bb6fe0d330482dbfdd106d93cf0cf84ace145`.

Merged into `engineering` as retained experimental evidence by squash commit `1626b9709766e41b77f34304daf8e5dae88e67e3`.

Files now present on `engineering`:
- `experiments/p117/README.md`
- `experiments/p117/openat2_beneath.c`
- `experiments/p117/run.sh`

Governance comment before merge: exact exercised attacks were `PROVEN_BY_TEST` only for the recorded Codex environment; P117 as a universal claim remained `UNPROVEN`; the experiment was not to be promoted to production architecture before independent adversarial review.

No PR-triggered GitHub Actions workflow run was returned when the original PR #2 head commit was queried through the GitHub API connector. This absence is not a PASS or FAIL classification for the experiment itself.

## Former PR #6 metadata

Title: `test: adversarially probe P117 traversal composition`

Original head commit: `342d1c404c555658f12a5a142e154b51e6329074`.

Merged into `engineering` as retained adversarial evidence by squash commit `6ddacfd483c79d395d56a4991cf91e7a2e9cb3b6`.

Files now present on `engineering`:
- `docs/security/P117_ADVERSARIAL_EVIDENCE.md`
- `tests/evil/p117_adversarial_probe.py`

The PR had no GitHub discussion comments at the time of this snapshot.

## CI evidence for former PR #6

GitHub Actions workflow: `Security Evil Tests`
Run: #26, id `32233103096`
Status: completed
Conclusion: success
Job: `security-evil-tests`, completed/success.

Important log details:
- runtime-confinement mutation tests passed;
- canonical OCI bundle lint passed;
- `bundle_toctou_binding.py` reported: `PASS: path reopen is TOCTOU-vulnerable; retained O_PATH identity is stable`;
- `mount_fd_binding_probe.py` reported: `SKIP: open_tree(OPEN_TREE_CLONE) unavailable/unprivileged: [Errno 1] Operation not permitted`.

Therefore the overall green workflow must not be interpreted as a successful privileged mount-binding proof. The mount probe was explicitly skipped/unproven inside a successful job.

## Reviewer instructions

Review the actual retained files on `engineering` together with this packet and the authoritative invariant/role documents. In particular:
- compare the materially different resolve policies used by Experimenter and Adversary;
- inspect whether any PASS wording overstates what the discriminator establishes;
- keep P117 containment separate from P118 object/manifest identity;
- treat mount-crossing as `UNPROVEN`;
- determine whether there is now a minimal Builder objective, or whether a further experiment is required.

Do not treat this packet's governance summaries as proof. The executable artifacts and reproducible tests remain the primary evidence.