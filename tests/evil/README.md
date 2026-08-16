# Evil tests

## Persistent credential authority

`persistent_credential_authority.c` probes Linux primitives that can create state or authority surviving a worker process and therefore make UID/GID reuse unsafe unless creation is structurally prevented.

### Build and run

```bash
gcc -O2 -Wall -Wextra -o persistent_credential_authority persistent_credential_authority.c
./persistent_credential_authority
./persistent_credential_authority --filtered
./persistent_credential_authority --exec-filtered
```

The third mode installs the SecurityFloor **before `exec`** and then execs the same binary in probe mode. This verifies that the seccomp floor survives `exec`.

### Evidence captured on 2026-08-16

Environment: Linux x86-64 harness available to the Engineering task.

Without the filter, all of the following primitives were actually available and succeeded in the harness:

- `shmget` (System V shared memory)
- `msgget` (System V message queue)
- `semget` (System V semaphore)
- `mq_open` (POSIX message queue)
- `memfd_create`
- `socket(AF_UNIX, ...)`
- `add_key` into the user keyring
- `keyctl` access to the user keyring

With the SecurityFloor installed at process start, every probe above returned `EPERM`.

With the SecurityFloor installed **before `exec`**, every probe above also returned `EPERM` after `exec`.

This is direct test evidence that the proposed pre-exec SecurityFloor can remove multiple Linux persistence/credential-authority creation primitives before untrusted runtime code starts. It supports P73–P76, especially `NoWorkerCredentialPersistentObjects`, but does **not** by itself prove safe UID reuse: filesystem writability, helper-created/chowned objects, all remaining IPC/keyring variants, namespaces, and the final syscall allowlist still require coverage.

### Pareto conclusion

Prefer **deny creation by construction** over a cleanup daemon that tries to discover every persistent Linux object after the worker exits. The eventual production profile should converge from this explicit deny test toward a small architecture-checked syscall allowlist derived from the real compilerless Wasmtime runtime.

## Filesystem authority policy

`test_filesystem_authority_policy.py` validates `security/runtime-filesystem-profile-v0.json` and mutation-tests the rule that Runtime Workers receive no durable writable filesystem authority.

Standard v0 currently requires:

- read-only worker rootfs;
- no durable writable paths;
- no writable mounts;
- no persistent path or object owned by the ephemeral worker UID/GID;
- no path opens or file creation after `READY`;
- explicit protection against shadowing runtime/native paths.

The mutation suite intentionally enables a writable rootfs, durable `/tmp`, persistent upload staging, a writable bind mount, a worker-owned cache, helper-materialized persistent ownership, post-READY opens, and post-READY file creation. Every mutation must be rejected.

This is an executable **policy proof**, not yet proof about the final launcher/container mount namespace. It prevents the design from silently reintroducing a durable writable path while the launcher is being built. The final proof must bind this profile to the effective runtime/mount configuration and demonstrate the same property against the real worker.
