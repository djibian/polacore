---
applyTo: "security/**,tests/evil/**,docs/security/**"
---

# Security-specific instructions

- Start from the relevant invariant and threat, not from the implementation's intended behavior.
- Prefer a reproducible counterexample over an architectural objection.
- For filesystem work, inspect root anchoring, descriptor binding, symlink/magiclink handling, mount crossing, special files, substitution races, and object identity assumptions.
- For runtime confinement, distinguish desired configuration from effective kernel-visible state.
- For authority, identify ambient authority, capability transfer, stale identity reuse, confused-deputy paths, and persistence.
- Any environmental inability to exercise a property remains `UNPROVEN`; do not translate it to PASS.
- New trusted code or privilege is a review concern even if functional tests are green.
- Reject hidden expansion from one invariant into adjacent invariants unless the issue explicitly authorizes it.
