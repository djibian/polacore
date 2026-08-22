# ADR-0003: Capability-based secure extension model

## Status

Accepted product direction. Concrete extension runtimes and sandbox mechanisms remain undecided and unproven.

## Context

PolaCore needs extensibility to support integrations, editor features, domain-specific behavior, and a future ecosystem. Reproducing the WordPress model in which installed plugins commonly share broad process, storage, and application authority would conflict with PolaCore's least-authority goals.

Different extension classes also have very different needs: an editor block, an outbound connector, a payment provider, and a server-side computation should not receive the same privileges or execution model.

## Decision

PolaCore will keep an extension system, but extensions receive **explicit capabilities** rather than implicit broad access.

Capabilities must be narrow, inspectable, and revocable where practical. Installation alone does not grant direct database, filesystem, network, secret, administrator, publication, or unrelated-component access.

Stable platform APIs and brokers mediate privileged operations. Extensions should declare the authority they require, and the platform should grant only the approved subset.

The extension model should support multiple classes with different authority ceilings, for example:

- **Declarative extensions** — schemas, presentation metadata, or constrained editor components with no general server authority.
- **UI/editor extensions** — extend PolaCore Studio through explicit editor APIs.
- **Connectors/automations** — access selected platform events and approved external services.
- **Commerce extensions** — payments, shipping, ERP/CRM, accounting, and similar integrations through PolaCommerce capabilities.
- **Isolated server extensions** — only when custom server computation is necessary, with explicit grants and an isolated execution boundary.

WebAssembly/WASI or another sandbox mechanism may be investigated for isolated server extensions. This ADR does not select that backend.

## Alternatives considered

### WordPress-compatible plugin execution

Rejected. Runtime compatibility with arbitrary WordPress plugin/theme code would import the authority model PolaCore is intended to replace.

### No extensions at all

Rejected. A closed CMS cannot realistically cover the diversity of integrations and specialized use cases required by a WordPress/WooCommerce replacement.

### One universal extension runtime

Not selected. The lowest-authority mechanism appropriate to each extension class is preferred over giving every extension the powers required by the most demanding cases.

## Security implications

- Capability definitions become security-sensitive public contracts.
- Extension manifests and grants must be reviewable and versioned.
- Platform APIs must enforce authorization independently of extension behavior.
- Network access must be explicit rather than ambient.
- Extension-to-extension access must be mediated rather than assumed.
- Sensitive operations such as publication, user administration, payment state changes, and secret access require dedicated capabilities.
- Removing or disabling an extension should revoke its continuing authority and must not leave hidden durable access paths.

## Evidence supporting the decision

This is a durable architecture direction authorized by the project owner and consistent with the project's existing least-authority and isolation goals. It does not claim that a concrete manifest format, broker API, sandbox, or revocation mechanism has been demonstrated.

## Consequences

- Extension APIs must be designed deliberately rather than exposing internal objects or storage.
- Common WordPress plugin functions should preferentially become native platform features or constrained extension APIs.
- PolaCommerce integrations become an important proving ground for capability design.
- WordPress migration translates recognized plugin semantics rather than importing their executable code.
- An extension marketplace, if created later, can expose requested capabilities to administrators as part of installation/review.

## Remaining uncertainty

- Capability taxonomy and granularity.
- Manifest/signing/distribution model.
- UI extension isolation and supply-chain policy.
- Isolated server runtime choice.
- Network mediation design.
- State ownership and upgrade/removal semantics.
- Human-readable permission UX without misleading users about residual risk.
