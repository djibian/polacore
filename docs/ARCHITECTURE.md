# PolaCore Architecture Baseline

## Status

This document records the current architectural baseline. It is not a substitute for evidence. Details may change when experiments or adversarial tests refute assumptions.

## High-level structure

PolaCore separates trusted authority from untrusted component execution.

Expected major trust domains:

- **Authority Core**: trusted authorization and high-value state transitions.
- **Broker / Storage services**: mediate explicitly authorized persistence and privileged operations.
- **Launch / confinement substrate**: creates restricted worker execution contexts from a narrow, versioned policy.
- **Third-party worker**: untrusted execution domain; arbitrary code execution is assumed possible.
- **Administrative surface**: trusted control plane; must not inherit authority from third-party content or code.

## Core architectural constraints

- No ambient authority for third-party workers.
- Component authority is explicit, narrow, revocable, and operation-scoped where practical.
- Worker compromise must not imply Authority Core compromise.
- Persistent authority must not depend solely on ephemeral UID/GID identity.
- Runtime confinement claims require inspection of effective runtime state, not just configuration text.
- Trusted executable artifacts must be bound to approved content/closure semantics and protected against substitution between validation and launch.
- Privileged launch mechanisms must expose a closed, versioned projection rather than arbitrary caller-controlled properties.

## Current engineering focus

The current prototype branch explores the security substrate before CMS product features. Recent work includes runtime-confinement policy validation, OCI-style configuration fixtures, adversarial tests, filesystem object identity, and anti-TOCTOU questions around trusted launch artifacts.

## Candidate runtime direction

Systemd transient units with `DynamicUser` remain a candidate launch substrate, but they are not accepted as secure merely because individual hardening properties are enabled. Effective properties, FD lifecycle, persistent-authority behavior, and projection soundness must be demonstrated.

A custom launcher remains an alternative only if it produces materially stronger or simpler evidence sufficient to justify additional privileged code and TCB.

## Architecture decision rule

When multiple mechanisms appear viable, prefer the mechanism with the smallest TCB and simplest operational model **provided that the required invariants can be demonstrated with equivalent confidence**.
