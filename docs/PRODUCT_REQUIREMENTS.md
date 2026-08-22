# PolaCore Product Requirements

## Status

This document records durable product requirements derived from real WordPress/WooCommerce usage and custom development experience. It defines expected capabilities and product allocation, not implementation mechanisms or demonstrated security properties.

These requirements do not change the current security-first sequencing. P117 and the security substrate remain the active engineering priority until governance changes that priority explicitly.

## Requirement source

The initial real-world reference set includes the following WordPress/WooCommerce capabilities currently used in production or custom projects:

- WooCommerce;
- Advanced Options for WooCommerce;
- Advanced Product Fields (Product Addons) for WooCommerce;
- Email Encoder;
- Import and export users and customers;
- PDF Invoices & Packing Slips for WooCommerce;
- custom `stmartin-plugin` for pedagogical e-commerce workflows;
- custom `stmartin-wof` for content types and taxonomies;
- Storefront Footer Text;
- WP Mail Logging;
- WP Menu Icons;
- Repeat Order for WooCommerce;
- Unit Price for WooCommerce;
- Cities Shipping Zones for WooCommerce;
- custom WordPress themes created because available themes were commonly too broad, too opinionated, or mismatched to the actual site need.

This inventory is a requirements input, not a promise to reproduce each plugin one-for-one.

## Native-versus-extension rule

A capability should preferentially be first-party when it is broadly useful and substantially defines a complete CMS, authoring/design environment, or commerce platform.

An extension should preferentially be used when the capability is:

- provider-specific;
- organization- or domain-specific;
- dependent on an external service or dataset;
- uncommon enough that first-party inclusion would add unjustified product complexity;
- executable custom behavior that cannot be represented safely as declarative data or an existing platform primitive.

**First-party does not mean kernel.** A native product capability may live in PolaStudio, PolaCommerce, a brokered first-party service, or another module outside the minimal trusted kernel.

When a real use case exposes a missing generic primitive, PolaCore should prefer extracting the reusable primitive instead of permanently encoding the whole use case as a privileged extension.

## PolaCore platform requirements

### PC-CORE-001 — Structured content model builder

PolaCore shall provide first-party modeling of structured content types, fields, relationships, taxonomies/classifications, validation rules, and reusable schemas so common custom-post-type/taxonomy helper plugins are unnecessary.

The model must be available through a stable programmatic contract and a PolaStudio visual authoring surface.

### PC-CORE-002 — User and account data portability

PolaCore shall provide explicit import/export for users and account-related data with schema validation, mapping, dry-run/reporting, conflict handling, and authorization appropriate to sensitive identity data.

PolaCommerce extends this capability for customer and commerce-specific records.

### PC-CORE-003 — First-party operational and audit observability

PolaCore shall expose first-party operational/audit history for important platform activity, including outbound-message events, authentication/security events, publication changes, failures, extension activity where observable, and other high-value administrative events.

Retention, access control, redaction, and privacy requirements must be explicit. Logging must not silently become a secret or personal-data dump.

### PC-CORE-004 — Stable navigation primitives

Navigation structures shall be native content/application primitives. Labels, destinations, hierarchy, visibility and semantic state belong to PolaCore data; their visual representation belongs to PolaStudio.

### PC-CORE-005 — Privacy-aware contact/address rendering

Publishing contact information such as email addresses shall not require arbitrary third-party code. PolaCore/PolaStudio shall offer first-party privacy-aware contact/rendering patterns.

Obfuscation or anti-harvesting techniques must not be represented as strong security guarantees without evidence. Safer alternatives such as mediated contact forms may be preferable depending on the use case.

## PolaStudio requirements

### PC-STUDIO-001 — Whole-site design environment

PolaStudio shall be the first-party environment for designing the whole site, not only individual page bodies.

It shall cover content authoring, site-wide visual design, reusable components, templates, navigation presentation, headers, footers, responsive behavior, and first-party commerce presentation surfaces.

### PC-STUDIO-002 — Design tokens

PolaStudio shall expose a structured design system including at least colors, typography, spacing, sizing constraints, radii, shadows, breakpoints, icon choices, and motion/animation policy where supported.

Site-wide visual decisions should be represented as reusable data rather than duplicated ad-hoc CSS.

### PC-STUDIO-003 — Reusable components and variants

Authors shall be able to create, configure and reuse structured components and variants so a design change can propagate consistently across all usages.

Components must preserve semantic structure and must not degrade into unrestricted arbitrary nesting as the default authoring model.

### PC-STUDIO-004 — Structured templates

PolaStudio shall support templates for content types and application surfaces, including standard pages, articles, archives/lists, search, products, product collections, cart, checkout, account/customer areas, and other future first-party modules.

Templates bind structured data to approved components rather than embedding arbitrary server-side code.

### PC-STUDIO-005 — Header, footer and navigation design

Header, footer, navigation styling, icons and similar whole-site presentation shall be directly configurable in PolaStudio. These functions shall not require dedicated feature plugins.

### PC-STUDIO-006 — Commerce form and document design

Where PolaCommerce exposes structured product options, checkout forms, invoices, credit notes, packing slips or delivery documents, PolaStudio shall provide first-party visual design/configuration surfaces over their canonical schemas.

Business invariants remain owned by PolaCommerce; Studio controls presentation and permitted layout/content choices.

### PC-STUDIO-007 — Declarative Site Design package

PolaStudio shall represent whole-site design through a declarative, versioned **Site Design** model/package containing at least:

- design tokens;
- typography and visual rules;
- component variants;
- templates;
- navigation/header/footer presentation;
- document and commerce presentation;
- assets/references;
- responsive rules.

A Site Design shall be visually editable, exportable, importable, duplicable and versionable.

### PC-STUDIO-008 — No ambient authority from design

A Site Design shall not acquire database, filesystem, network, secret, administrator, publication, or server-execution authority merely because it controls presentation.

Functional behavior requiring executable code belongs to a constrained first-party component or Secure Extension with explicit capabilities.

### PC-STUDIO-009 — Advanced styling escape hatch

PolaStudio should provide an advanced styling mechanism for cases not expressible through normal design controls, but it must be scoped, inspectable and separated from server authority.

The exact supported CSS/custom-style model remains an implementation question.

## PolaCommerce requirements

### PC-COM-001 — Structured product options and add-ons

PolaCommerce shall natively model configurable product options/add-ons/custom fields, including reusable/global option groups, validation and conditional visibility/availability where justified.

PolaStudio shall provide the visual authoring and rendering configuration for these structures.

### PC-COM-002 — Unit-aware quantity and pricing

PolaCommerce shall support products whose commercial quantity, pricing basis, display unit, inventory unit, or fulfillment unit differ.

The model must be expressive enough for cases such as selling by item while calculating price by weight or other measurement, without requiring a general-purpose plugin.

### PC-COM-003 — Reorder

Customers shall be able to create a new cart/order intent from a previous order when the referenced products/options remain valid and purchasable. Changed price, availability and configuration must be revalidated rather than blindly copied.

### PC-COM-004 — Geographic shipping rules

PolaCommerce shall provide a first-party shipping-zone/rule model capable of using geographic attributes such as country, region/state, postal code and city/locality where appropriate.

Large or jurisdiction-specific geographic datasets may be distributed as data packs or extensions rather than embedded in the minimal product.

### PC-COM-005 — First-party commercial documents

PolaCommerce shall own canonical business data and lifecycle rules for invoices, credit notes, packing/preparation slips and delivery documents where in product scope.

PolaStudio shall control their permitted visual templates. Provider/jurisdiction-specific electronic invoicing transports or external accounting integrations may be extensions.

### PC-COM-006 — Commerce data portability

PolaCommerce shall expose explicit import/export/migration of products, customers, orders and other supported commerce records with validation, mapping, conflict reporting and security controls.

### PC-COM-007 — Provider extension points

Payments, shipping carriers, ERP/CRM, accounting, tax services and similar providers shall integrate through narrow PolaCommerce capabilities and stable APIs rather than broad CMS authority.

### PC-COM-008 — Advanced commerce option inventory

The actual behaviors used from Advanced Options for WooCommerce shall be inventoried before implementation planning. Each behavior shall be classified as:

- generic PolaCommerce capability;
- PolaStudio presentation/configuration capability;
- provider/domain-specific Secure Extension;
- unnecessary compatibility behavior.

No one-to-one port of the plugin is required.

## Secure Extension requirements

### PC-EXT-001 — Saint-Martin pedagogical workflow

The custom `stmartin-plugin` shall initially be treated as a domain-specific Secure Extension.

Its behavior shall be decomposed during migration analysis. Generic reusable primitives discovered in that analysis should be candidates for first-party PolaCore/PolaStudio/PolaCommerce capabilities, leaving only genuinely pedagogical policy in the extension.

### PC-EXT-002 — External provider connectors

Payment, shipping, ERP/CRM, accounting and similar provider connectors shall be Secure Extensions unless a specific integration is deliberately adopted as first-party infrastructure.

They receive only the capabilities required for their role.

### PC-EXT-003 — Data packs and external datasets

Large external datasets, such as locality/shipping-zone data, may use a constrained data-pack/extension mechanism when that reduces maintenance and update coupling without granting executable authority unnecessarily.

## WordPress/WooCommerce migration requirements

### PC-MIG-001 — Semantic plugin classification

The migrator shall classify source WordPress/WooCommerce plugins by the function they provide, not merely by plugin slug/name.

The migration report should map recognized functionality to one of:

- native PolaCore;
- native PolaStudio;
- native PolaCommerce;
- approved Secure Extension;
- unsupported / requires analysis.

### PC-MIG-002 — Theme to Site Design translation

The migrator should translate recoverable WordPress theme semantics into the PolaStudio Site Design model: tokens/styles, templates, navigation/header/footer presentation, assets and responsive rules where deterministically recoverable.

### PC-MIG-003 — No silent import of executable theme/plugin behavior

Executable WordPress theme/plugin behavior that has no safe native or extension mapping must be reported explicitly. It must not be silently imported or executed inside PolaCore.

### PC-MIG-004 — Requirement traceability from real sites

Migration development shall retain anonymized/appropriate functional inventories from real source sites as test cases so product coverage is driven by actual needs rather than abstract WordPress feature parity.

## Initial source-to-target mapping

| WordPress/WooCommerce capability | Primary PolaCore target | Requirement rationale |
| --- | --- | --- |
| WooCommerce | PolaCommerce | First-party commerce product scope |
| Advanced Options for WooCommerce | PolaCommerce / PolaStudio / extension after per-option analysis | Avoid plugin-level compatibility; classify individual semantics |
| Advanced Product Fields | PolaCommerce + PolaStudio | Product configuration is a generic commerce capability with visual authoring |
| Email Encoder | PolaCore + PolaStudio | Contact/privacy rendering should not require arbitrary code |
| Import/export users/customers | PolaCore + PolaCommerce | Data portability is first-party platform behavior |
| PDF Invoices & Packing Slips | PolaCommerce + PolaStudio | Business data/lifecycle native; visual document design native |
| `stmartin-plugin` | Secure Extension, with generic primitives extracted if found | Pedagogical/domain-specific policy |
| `stmartin-wof` | PolaCore + PolaStudio | Structured content modeling should be native |
| Storefront Footer Text | PolaStudio | Whole-site presentation capability |
| WP Mail Logging | PolaCore | Operational/audit observability |
| WP Menu Icons | PolaStudio | Navigation presentation capability |
| Repeat Order for WooCommerce | PolaCommerce | Generic customer/order workflow |
| Unit Price for WooCommerce | PolaCommerce | Generic unit-aware commercial model |
| Cities Shipping Zones for WooCommerce | PolaCommerce + optional data pack | Generic rule engine, potentially external data |
| Custom WordPress themes | PolaStudio Site Design + constrained components/extensions | Presentation becomes declarative; executable behavior separated |

## Theme terminology

PolaCore may use the word **theme** in migration UI or user-facing language if useful for familiarity, but the architecture must not reintroduce a WordPress-style privileged executable theme package.

The canonical product concept is **Site Design**: declarative presentation data owned and edited by PolaStudio.

## Open implementation questions

These requirements intentionally do not decide:

- the exact Site Design schema;
- the exact component schema and responsive model;
- how much advanced CSS is allowed and how it is scoped;
- the editor engine used inside PolaStudio;
- electronic invoicing jurisdiction/provider coverage;
- the geographic dataset/update mechanism;
- the capability taxonomy for provider extensions;
- the exact extraction of generic primitives from `stmartin-plugin`;
- the exact Advanced Options for WooCommerce behavior set that must be reproduced natively.
