# PolaCore Security Model

## Primary adversary

Assume a third-party component obtains arbitrary code execution inside its worker. The architecture must remain safe under that condition.

## Assets to protect

- administrator identity and role authority;
- publication authority;
- trusted/admin JavaScript and trusted code;
- secrets and unauthorized content/data;
- other components and their state;
- Authority Core and Broker authority;
- host filesystem and arbitrary database authority;
- ambient network access;
- durable credentials and persistence mechanisms.

## Trust boundaries

### Trusted

The minimal Authority Core and narrowly scoped trusted services required to authorize, broker, store, and launch operations.

### Conditionally trusted

Runtime/OS mechanisms such as systemd, kernel namespaces, seccomp, cgroups, filesystem primitives, and Wasmtime are relied upon only for properties that are explicitly understood and demonstrated in the deployed configuration.

### Untrusted

- third-party component code;
- component packages and archives;
- migration inputs;
- component-supplied manifests and metadata;
- component IPC payloads;
- files and paths inside attacker-controlled staging areas;
- generated code or content not yet promoted into a trusted closure.

## Threat classes

The security program actively tests at least:

- privilege escalation;
- confused deputy and authority inheritance;
- cross-component compromise;
- secret/data exfiltration;
- publication bypass;
- network and filesystem ambient authority;
- file-descriptor leakage;
- runtime-property injection;
- namespace/mount escape;
- TOCTOU and object substitution;
- stale UID/GID or credential reuse;
- persistence after worker termination;
- lifecycle and cleanup failures;
- crash-consistency failures;
- supply-chain and migration poisoning;
- false-positive tests and misleading CI.

## Evidence policy

Security claims must distinguish configuration/policy evidence from effective runtime evidence. A policy linter proves properties of policy input only; it does not by itself prove the launched process has those properties.

Failures to exercise a property due to missing privileges or environment limitations must be reported as `UNPROVEN` or explicit `SKIP`, never as success.

## Security posture

PolaCore prefers structural prevention over detection and cleanup. An authority that should never reach a worker should not be made available and then merely filtered by convention.
