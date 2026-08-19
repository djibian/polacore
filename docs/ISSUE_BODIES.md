# Seed issue content

This file records the intended initial structure of the permanent governance issues so it remains reviewable in Git history.

## `[Lead] PolaCore state & priorities`

- Current phase: security substrate / trusted launch path.
- Demonstrated baseline: policy/configuration validation and Evil-test CI exist on `engineering`; effective runtime guarantees remain narrower than configuration guarantees.
- Highest-value uncertainty: safe, bounded traversal and materialization of attacker-controlled staging into a trusted launch closure without path escape or substitution.
- Active invariant: P117, followed by P118-P120.
- Current next action: run a bounded P117 experiment before broader production implementation.
- Deferred: CMS product features, broad plugin compatibility, UI, fs-verity hardening, and `main` promotion.

## `[Security] PolaCore threat & attack log`

Initial high-priority attack families:

- staging symlink and magiclink escape;
- ancestor rename / traversal race;
- mount crossing where test environment permits;
- source mutation during copy;
- hardlink / alias retention into trusted closure;
- publication crash consistency and concurrent promotion;
- effective runtime drift between declared policy and launched process;
- FD duplication/lifecycle and persistent-authority reuse.
