# ADR-0002: PolaCommerce is a first-party module outside the minimal kernel

## Status

Accepted product direction. Commerce internals remain undecided and unproven.

## Context

E-commerce is essential to PolaCore's ability to replace WordPress/WooCommerce for important real-world sites. At the same time, embedding the entire commerce domain inside the minimal CMS kernel would increase complexity for every installation, including sites that do not sell anything.

Commerce also depends on many external integrations such as payment providers, shipping services, ERP/CRM systems, accounting tools, and tax services.

## Decision

PolaCore will include **PolaCommerce** as an official, first-party, maintained product module.

PolaCommerce is essential product scope and should feel natively integrated with PolaCore, but it remains separable from the minimal kernel.

The expected domain includes products, variants, inventory, carts, checkout, orders, customers, promotions, taxation, shipping, payments, and commerce APIs. Exact scope and implementation order will be decided incrementally.

External commerce integrations must use the same explicit-capability extension model as the rest of PolaCore. A payment or shipping integration receives only the platform capabilities needed for its role.

## Alternatives considered

### Put commerce directly in the kernel

Rejected. This would impose commerce-specific code and complexity on all sites and make it harder to preserve a small trusted core.

### Leave commerce entirely to third-party extensions

Rejected. Commerce is too important to the product target and migration story to depend on an ordinary extension with no first-party architectural ownership.

### Reuse WooCommerce as a runtime dependency

Rejected. WooCommerce remains a migration source and functional reference, not a runtime authority model for PolaCore.

## Security implications

- The kernel/commerce boundary must be expressed through explicit service APIs.
- Commerce-specific sensitive state and operations require narrowly defined authorization rules.
- Payment, shipping, and external business connectors must not gain unrelated CMS authority.
- Non-commerce deployments should not need to enable PolaCommerce services or their integrations.

## Evidence supporting the decision

This is a product-boundary decision authorized by the project owner. It does not claim that a commerce architecture, payment model, or transaction design has already been validated.

## Consequences

- PolaCommerce becomes a first-class roadmap area after the security substrate and foundational CMS contracts are credible.
- WooCommerce migration can target a known first-party domain model rather than a generic plugin layer.
- Commerce integrations become a major test case for the secure extension architecture.
- The kernel must expose stable primitives sufficient for PolaCommerce without absorbing commerce-specific policy.

## Remaining uncertainty

- Exact commerce domain model and transaction boundaries.
- Order/payment state machines and idempotency rules.
- Tax, shipping, inventory, refund, subscription, and marketplace scope.
- Storage/service partitioning between kernel and PolaCommerce.
- Migration coverage across WooCommerce versions and extensions.
