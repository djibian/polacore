# PolaCore Architecture Baseline

## Status

This document records the current architectural baseline. It is not a substitute for evidence. Details may change when experiments or adversarial tests refute assumptions.

## High-level structure

PolaCore separates trusted authority from untrusted component execution.

Expected major trust domains:

- **Authority Core**: trusted authorization and high-value state transitions.
- **Broker / Storage services**: mediate explicitly authorized persistence and privileged operations.
- **Launch / confinement substrate**: creates restricted worker execution contexts from a narrow, versioned policy.
- **Third-party worker**: untrusted execution domain; only explicitly granted authority is available.
- **Administrative surface**: trusted control plane; must not inherit authority from third-party content or code.

## Core architectural constraints

- No ambient authority for third-party workers.
- Component authority is explicit, narrow, revocable, and operation-scoped where practical.
- Worker failure or compromise must not imply Authority Core compromise.
- Persistent authority must not depend solely on ephemeral UID/GID identity.
- Runtime confinement claims require inspection of effective runtime state, not just configuration text.
- Trusted executable artifacts must be bound to approved content/closure semantics and protected against substitution between validation and launch.
- Privileged launch mechanisms must expose a closed, versioned projection rather than arbitrary caller-controlled properties.

## Future product-layer boundaries

The security substrate is intended to support the following product architecture once its invariants are sufficiently demonstrated:

```text
PolaCore Studio
  |  native structured authoring
  v
Typed/versioned PolaCore document model
  |
  +--> rendering / delivery
  +--> data bindings / forms
  +--> migration transforms

PolaCommerce
  |  official first-party module
  v
Stable PolaCore service APIs

Secure Extensions
  |  explicit capability grants
  v
Brokered services / isolated execution
  |
  v
Authority Core
```

### PolaCore Studio

PolaCore Studio is the first-party authoring environment. Its canonical persisted content is a PolaCore-owned typed and versioned tree/document representation, not rendered HTML and not the private state format of a third-party editor library.

A rich-text engine may be embedded for text editing, but it remains replaceable. Candidate technologies such as ProseMirror/Tiptap and Lexical require separate evaluation before selection.

The editor should expose direct visual composition while preserving structural and semantic constraints. Page-builder-style unrestricted presentation nesting is not an architectural goal.

### PolaCommerce

PolaCommerce is an official first-party module and essential product scope, but it is not part of the minimal kernel. This boundary lets non-commerce installations avoid unnecessary commerce code and lets commerce-specific authority be modeled explicitly.

Payment, shipping, ERP/CRM, accounting, and similar integrations are expected to connect through the same capability-oriented extension architecture rather than receiving general CMS authority.

### Secure extension platform

PolaCore remains extensible. Extensions interact with the platform through explicit capabilities and stable APIs instead of implicit access to internal storage or privileged services.

The execution mechanism should be selected according to the extension class and required authority. Declarative/editor extensions should use low-authority mechanisms; external connectors should receive scoped service access; server-side third-party components require isolation. WebAssembly/WASI is a candidate for later experiments, not an accepted architecture backend.

### Migration boundary

WordPress and WooCommerce are migration sources, not execution environments inside PolaCore. Migration tooling should translate recognized content and application semantics into the PolaCore document model, PolaCommerce, native platform features, or approved extensions.

Compatibility with arbitrary WordPress plugin/theme executable code is explicitly outside the target architecture.

## Current engineering focus

The current prototype branch explores the security substrate before CMS product features. Recent work includes runtime-confinement policy validation, OCI-style configuration fixtures, adversarial tests, filesystem object identity, and anti-TOCTOU questions around trusted launch artifacts.

The future product-layer decisions above do **not** reprioritize this work. They constrain later design so that authoring, commerce, migration, and extensions are built on the demonstrated authority model rather than bypassing it.

## Candidate runtime direction

Systemd transient units with `DynamicUser` remain a candidate launch substrate, but they are not accepted as secure merely because individual hardening properties are enabled. Effective properties, FD lifecycle, persistent-authority behavior, and projection soundness must be demonstrated.

A custom launcher remains an alternative only if it produces materially stronger or simpler evidence sufficient to justify additional privileged code and TCB.

## Architecture decision rule

When multiple mechanisms appear viable, prefer the mechanism with the smallest TCB and simplest operational model **provided that the required invariants can be demonstrated with equivalent confidence**.
