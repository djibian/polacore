# Architecture Decision Records

Use ADRs only for durable architectural decisions whose trade-offs should remain understandable after the related issue is closed.

Naming convention:

`ADR-NNNN-short-decision-name.md`

Each ADR should record:

- context;
- decision;
- alternatives considered;
- security implications;
- evidence supporting the decision;
- consequences and remaining uncertainty.

Do not create an ADR for every experiment. Failed hypotheses and temporary investigations belong in their GitHub issues and experimental PRs.

## Accepted product-direction ADRs

- [ADR-0001 — Native structured editor and PolaCore-owned document model](ADR-0001-native-structured-editor.md)
- [ADR-0002 — PolaCommerce is a first-party module outside the minimal kernel](ADR-0002-polacommerce-first-party-module.md)
- [ADR-0003 — Capability-based secure extension model](ADR-0003-capability-based-extension-model.md)

These ADRs define durable product boundaries. They do not select implementation mechanisms that still require experiments and evidence.
