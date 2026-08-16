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

## Runtime confinement policy

`test_runtime_confinement_policy.py` validates the single source of policy truth, `security/runtime-confinement-profile-v0.json`, and mutation-tests both the abstract Standard v0 policy and a representative effective OCI runtime configuration.

Standard v0 currently requires:

- read-only worker rootfs;
- no durable writable paths;
- no persistent path or object owned by the ephemeral worker UID/GID;
- no runtime-added mounts;
- no OCI lifecycle hooks;
- private rootfs mount propagation;
- `noNewPrivileges=true`;
- no path opens or file creation after `READY`;
- explicit protection against shadowing runtime/native paths.

The mutation suite intentionally enables a writable rootfs, durable `/tmp`, worker-owned persistent state, post-READY opens/creation, shared mount propagation, lifecycle hooks, writable bind mounts, and even **read-only bind mounts that shadow `/app/lib` or `/usr/lib`**. Every mutation must be rejected.

This is an executable **policy/configuration proof**, not yet proof about the final launcher or a real OCI runtime mount namespace. It prevents the design from silently reintroducing filesystem authority and catches the important distinction between an authentic image and a dangerous effective runtime configuration. The final proof must bind this profile to the configuration actually used to create the worker and demonstrate the same property against the real runtime.
