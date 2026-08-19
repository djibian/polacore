# Independent review of retained P117 evidence

Date: 2026-08-19  
Role: Reviewer  
Issue: #5  
Invariant: P117, `SourceTraversalCannotEscapeStaging`

## Review decision

The retained artifacts support a narrow Linux `openat2(2)` containment result,
not complete P117 traversal. On the exercised Linux x86-64 kernel, opens made
relative to a stable staging directory descriptor did not reach the adjacent
sentinel through the tested lexical escape, absolute path, outside symlink,
ancestor rename, or finite symlink-swap cases. The separate deterministic
adversarial probe also showed that `RESOLVE_BENEATH | RESOLVE_NO_MAGICLINKS`
rejected its two absolute outside-symlink cases.

P117 remains `UNPROVEN` as a complete invariant. Neither artifact implements or
exercises recursive enumeration and materialization. Mount crossing was not
exercised. The artifacts also demonstrate that containment is not object
identity and that resolve flags are not an object-type policy.

No product implementation is approved by this review. A minimal Builder
objective can be stated, but work remains gated on the Lead explicitly marking
issue #5 ready for build.

## Artifact and policy comparison

The Experimenter opens data with
`O_RDONLY | O_CLOEXEC | O_NOFOLLOW` and the strict policy:

```text
RESOLVE_BENEATH | RESOLVE_NO_MAGICLINKS | RESOLVE_NO_SYMLINKS | RESOLVE_NO_XDEV
```

This policy rejects every symlink component and every mount-point crossing. It
is consistent with treating symlinks as data, but the experiment never
implements the separate descriptor-relative inspection/readlink operation that
would be needed to preserve a symlink as data.

The Adversary's ordinary cases instead use:

```text
RESOLVE_BENEATH | RESOLVE_NO_MAGICLINKS
```

and add `RESOLVE_NO_XDEV` only to the mount case. It deliberately omits
`RESOLVE_NO_SYMLINKS` and `O_NOFOLLOW`, so ordinary symlinks may be followed if
resolution remains beneath the root. This is a materially more permissive
policy, useful for attacking the containment boundary but not equivalent to the
Experimenter's candidate. Its results must not be presented as independent
execution of the exact candidate policy.

Both probes use a stable `O_PATH | O_DIRECTORY | O_CLOEXEC` root descriptor.
The Experimenter's ancestor-rename case supports the narrow claim that later
relative resolution remains anchored at that opened directory object rather
than a replacement installed at its former pathname.

## Claim classification

| Claim | Review classification | Basis and boundary |
| --- | --- | --- |
| A valid ordinary in-root file can be opened by the Experimenter policy. | `PROVEN_BY_TEST` | The control read succeeded in the retained probe and this review run. This is compatibility evidence for the recorded environment only. |
| The Experimenter policy rejects the exact `../outside` and absolute-path attempts. | `PROVEN_BY_TEST` | Both returned `EXDEV`; no outside bytes were opened. This does not establish every lexical/canonical namespace rule in P119. |
| The Experimenter policy does not follow the exact outside symlink. | `PROVEN_BY_TEST` | The open returned `ELOOP` under `RESOLVE_NO_SYMLINKS`. |
| The Experimenter's `/proc/self/fd/N`-targeting symlink is not followed. | `PROVEN_BY_TEST`, narrowed | `RESOLVE_NO_SYMLINKS` rejects the ordinary symlink before the probe discriminates magic-link handling. It proves non-following under the combined strict policy, not an independent `RESOLVE_NO_MAGICLINKS` magic-link result. |
| A stable root descriptor remains attached to the original directory across rename and pathname replacement. | `PROVEN_BY_TEST` for the exact case | The replacement contained the sentinel while the descriptor-relative open returned original content. It says nothing about identity of entries subsequently replaced inside that directory. |
| The 20,000-iteration race observed no read of the exact outside sentinel. | `PROVEN_BY_TEST` for that finite run | The result is an observed absence, not exhaustive race proof. |
| The race's reported `inside_reads` were all verified reads of inside content. | `REFUTED` by code inspection | The counter increments for every successful open unless one read returns the complete exact outside sentinel. Read errors, short reads, empty reads, or other content are also counted as `inside_reads`. |
| The race definitely overlapped an open with a symlink state. | `UNPROVEN` | The child performs swaps, but the parent records no errno distribution or synchronization proving an attempted open observed the symlink. A nonzero aggregate `denied` count can also include `ENOENT`. |
| `RESOLVE_BENEATH | RESOLVE_NO_MAGICLINKS` rejects the Adversary's deterministic absolute outside symlink substitution. | `PROVEN_BY_TEST` | The exact substitution returned `EXDEV` on the recorded environment and this review run. It is not all schedules or all symlink topologies. |
| The Adversary independently exercised a proc magic link. | `UNPROVEN` / misleading `PASS` | The staged object is an ordinary absolute symlink whose text is `/proc/self/fd/0`. `RESOLVE_BENEATH` can reject that absolute symlink before `/proc` lookup or magic-link evaluation. The code comment acknowledges this, so the emitted `magic_link_path: PROVEN_BY_TEST` overstates the discriminator. What is proven is rejection of this second absolute outside symlink path. |
| Enumeration followed by constrained pathname open preserves the enumerated object's identity. | `REFUTED` | Deterministic replacement produced different `(st_dev, st_ino)` and substituted bytes while staying beneath the root. This is not a P117 containment failure; it is directly relevant to the P118 boundary. |
| Resolve flags reject special objects. | `REFUTED` | `openat2` returned an `O_PATH` descriptor for the in-root FIFO. Explicit post-open type validation is required before a blocking or side-effecting data open. |
| `RESOLVE_NO_XDEV` rejects a bind-mount crossing in the retained environment. | `UNPROVEN` | Both retained runners lacked mount authority. The visible `UNPROVEN` result remains correct even if a containing workflow/job is green. |
| The candidate provides safe recursive traversal/materialization. | `UNPROVEN` | There is no recursive enumerator or materializer, no directory-entry race composition, and no demonstrated symlink-as-data operation. |
| P117 is fully established across supported kernels/filesystems. | `UNPROVEN` | Only one recorded kernel/environment and this review environment were exercised; supported-platform behavior and hostile/filesystem-specific semantics are not established. |

## Discriminator and reporting defects

### Blocking for any complete-P117 claim

1. **No traversal composition exists.** Supplying isolated names to `openat2`
   does not demonstrate safe recursion, directory descent, or later reads.
2. **Mount crossing is untested.** `RESOLVE_NO_XDEV` is configured by the
   Experimenter, but configuration text is not runtime evidence.
3. **The race counter is mislabeled.** `inside_reads` means only “successful
   opens not followed by an exact full sentinel match,” not verified inside
   reads. This weakens the result but does not erase the narrower observation
   that the exact sentinel was not observed.
4. **Symlink-race exercise is not positively discriminated.** No synchronization
   or errno accounting establishes that a parent open actually encountered the
   symlink state.
5. **The Adversary's magic-link `PASS` is misleading.** It does not establish
   that magic-link resolution was reached. It should be described as rejection
   of an absolute symlink targeting a representative magic-link namespace.
6. **Special-object rejection is absent by design and refuted as an implicit
   property.** A future implementation needs an explicit allowlist based on the
   opened object, not a pre-open pathname observation alone.

### Optional experiment hardening

- Make the race child and parent synchronize distinct regular-file and symlink
  phases, record errno classes, verify all successful-read content, and call the
  counter `successful_opens` unless content is actually checked.
- Exercise a real magic link without first making absolute-symlink rejection the
  deciding condition, if a staging/mount topology capable of doing so can be
  constructed safely.
- Run mount-crossing cases in a disposable user/mount namespace or dedicated CI
  job that can honestly create the fixture, including a crossing introduced
  during traversal.
- Expand special-object probes only where they model authority an actual staging
  producer can possess; do not turn inability to create an object into PASS.

These improvements are necessary before upgrading their respective evidence,
but they do not need to block a deliberately narrow helper implementation whose
claims exclude those properties.

## P117 versus P118

P117 asks whether a read can escape the stable staging root. The ordinary
in-root substitution remains contained and therefore does not refute the narrow
P117 containment evidence. P118 asks whether materialized bytes and semantics
match an already approved identity. The substitution demonstrates that an
enumerated pathname observation cannot supply that binding.

A Builder must therefore avoid both category errors:

- do not claim that containment binds a pathname to the object previously
  enumerated or approved; and
- do not treat a different attacker-chosen in-root object as trusted merely
  because the open stayed beneath the root.

The future P118 design must compare the acquired object's complete required
semantics to the approved manifest and fail on mutation. That work is explicitly
outside this P117 review.

## Safe minimal Builder objective

A minimal objective can now be stated safely, subject to Lead approval:

> Implement a Linux-only, fail-closed source-acquisition primitive that holds a
> stable staging-root descriptor; accepts only canonical relative path
> components; acquires each object descriptor-relatively with the strict
> `RESOLVE_BENEATH | RESOLVE_NO_MAGICLINKS | RESOLVE_NO_SYMLINKS |
> RESOLVE_NO_XDEV` policy; inspects the acquired object through its descriptor;
> and accepts only an explicit object-type allowlist before any data read.
> Unsupported `openat2` or resolve-flag behavior must fail closed. Add
> deterministic negative tests for lexical/absolute escape, outside symlink,
> ancestor replacement, in-root substitution, FIFO/special-object rejection,
> and mount crossing where the test environment can genuinely exercise it.

The objective must retain these boundaries:

- It is not approval to build the entire promotion backend.
- It must not claim P118 manifest/object identity, P119 namespace completeness,
  or P120 publication/crash consistency.
- Symlinks may be rejected initially. If they must be retained as data, their
  descriptor-relative, race-safe capture requires a separately specified and
  tested operation; silently following them is prohibited.
- A test environment that cannot create a mount fixture must report that case as
  `SKIP`/`UNPROVEN`, not PASS, and the P117 claim remains correspondingly
  narrowed.
- Recursive directory traversal is not proven merely by implementing this
  primitive. Integration must retain descriptor anchoring at every descent and
  receive its own adversarial review before complete P117 is claimed.

This is sufficiently bounded for a Builder increment because it makes the
known refutations explicit and does not require inventing P118 architecture.
It is not evidence that the increment has already been implemented or that
complete P117 is ready to close.

## Remaining uncertainty

- real and concurrently introduced mount crossings;
- recursive enumeration/descent and rename/substitution composition;
- race-safe treatment of symlinks as data;
- sockets, device nodes, hardlinks, and metadata-bearing objects under the
  actual staging producer's authority;
- supported kernel, libc/ABI, and filesystem matrix;
- hostile network/FUSE or filesystem-specific semantics;
- all P118 object/manifest identity and mutation-during-copy properties.

## Reproduction performed for this review

```sh
./experiments/p117/run.sh
python3 tests/evil/p117_adversarial_probe.py
```

Both commands completed successfully as programs. The first printed
`UNPROVEN` for mount crossing, and the second emitted an `UNPROVEN`
mount-crossing record. Those environment-limited cases are not passes.
