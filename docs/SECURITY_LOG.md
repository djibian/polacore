# PolaCore Security Threat & Attack Log

This file is a fallback repository copy of the state that should normally be maintained in the permanent GitHub issue `[Security] PolaCore threat & attack log`.

## Current highest-value attack families

1. staging symlink and magiclink escape;
2. ancestor rename / source traversal race;
3. mount crossing where the environment permits testing;
4. source mutation during copy or hashing;
5. hardlink / retained-handle alias into trusted closure;
6. concurrent publication and crash consistency;
7. effective runtime drift between declared confinement policy and launched process;
8. file-descriptor duplication/lifecycle ambiguity;
9. persistent authority from recycled ephemeral identity.

## Current Security Lab request

Independently attack the P117 experiment once it produces a concrete traversal primitive. Prioritize counterexamples that cause host data outside staging to be read while the experiment still reports success.

## Evidence rule

A theoretical attack is useful for prioritization, but closure requires reproducible evidence. Environmental inability to exercise an attack remains explicit `UNPROVEN` or `SKIP`.
