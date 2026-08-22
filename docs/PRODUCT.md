# PolaCore Product

## Purpose

PolaCore is an experimental secure CMS and component platform designed around least authority, strong isolation, explicit capabilities, and verifiable security invariants.

The project is not a WordPress hardening fork. WordPress may be used as a migration appliance, compatibility source, or adversarial benchmark, but it is not the authority model for PolaCore.

## Product direction

PolaCore aims to cover the important uses of WordPress without reproducing its historical architecture.

The long-term product has four first-class layers:

1. **PolaCore Kernel** — the smallest practical trusted CMS core for identity, authorization, content, media, publication, versioning, and stable APIs.
2. **PolaCore Studio** — a first-party modern visual editor built around a typed and versioned structured-content model rather than page-builder markup or HTML as the canonical source.
3. **PolaCommerce** — an official first-party commerce module, deeply integrated with PolaCore but separable from the minimal kernel.
4. **Secure Extensions** — an extension ecosystem based on explicit capabilities, stable APIs, least authority, and isolation rather than implicit broad access.

A strategic fifth capability is the **WordPress/WooCommerce migration system**, which translates sites into native PolaCore concepts instead of importing legacy executable components.

## Core product promise

A third-party component may be fully compromised without thereby obtaining authority over the CMS core, administrators, publication, secrets, unrelated components, ambient storage, arbitrary network access, or durable persistence.

## Native authoring direction

PolaCore will ship its own editor. Gutenberg is an important reference and migration source, but PolaCore is not constrained to reproduce Gutenberg's persistence format or interaction model.

The canonical content representation should be a typed, versioned document/tree model that can represent structured content, reusable components, layout, responsive intent, design tokens, dynamic data bindings, forms, and future authoring features without making rendered HTML the source of truth.

The editor should provide direct visual editing and powerful composition while preserving semantic structure. General-purpose page-builder behavior that encourages arbitrary presentation nesting is not the target.

Rich-text/editor engines such as ProseMirror/Tiptap or Lexical may be evaluated as implementation components. No third-party editor engine is currently selected, and no such engine may become the persistence authority for PolaCore content.

## Commerce direction

E-commerce is essential product scope. PolaCommerce is therefore a first-party product module, not an optional afterthought and not an ordinary third-party extension.

It is intentionally outside the minimal kernel so sites that do not need commerce do not automatically inherit its full complexity and integrations.

PolaCommerce is expected eventually to cover products, variants, inventory, carts, checkout, orders, customers, promotions, taxation, shipping, payments, and commerce APIs. External payment, shipping, ERP, CRM, accounting, and similar integrations should use the secure extension capability model.

## Extension direction

PolaCore remains extensible, but WordPress-style implicit plugin authority is a non-goal.

Extensions must receive explicit, narrow, reviewable authority. Database, filesystem, network, secret, administrator, publication, and other privileged access are never implied merely by installation.

Different extension classes may use different execution mechanisms. Declarative editor extensions should need little or no server authority; connectors and automation should receive scoped APIs; third-party server components require isolation and explicit capability grants. WebAssembly/WASI or other sandbox mechanisms may be investigated, but no backend is selected yet.

## Migration direction

PolaCore is a **destination for WordPress migration**, not a runtime compatibility layer for WordPress PHP components.

The migration system should progressively understand WordPress core content, Gutenberg structures, WooCommerce data, common themes/page builders, and widely used plugins. Where possible it should map their semantics to native PolaCore/PolaCommerce features or approved extensions.

Examples include mapping SEO metadata to native SEO capabilities, form plugins to native forms, WooCommerce catalogue/order data to PolaCommerce, and recognized payment/shipping integrations to corresponding secure extensions.

Unknown or custom plugins should be analyzed and reported rather than silently imported as executable components. Direct execution of WordPress plugins or themes inside PolaCore is a non-goal.

## Native-versus-extension inclusion rule

PolaCore should not use an extension merely because WordPress historically required a plugin for the same function.

A broadly useful capability that materially defines a complete CMS, authoring/design environment, or commerce platform should preferentially be implemented as a first-party capability in the appropriate product layer. Provider-specific, organization-specific, domain-specific, unusually specialized, or externally coupled behavior should preferentially remain a Secure Extension.

This rule must not be used to enlarge the minimal trusted kernel indiscriminately. First-party capabilities may live in PolaStudio, PolaCommerce, brokered services, or other modules outside the kernel.

Real use cases should be decomposed into reusable primitives. When a custom plugin exposes a missing generic primitive, that primitive should be considered for the first-party platform while genuinely domain-specific policy remains in the extension.

## Whole-site design direction

PolaStudio is the whole-site design environment, not only the page editor.

PolaCore will not reproduce WordPress-style executable themes as a privileged application unit. Whole-site presentation is represented by a declarative, versioned **Site Design** model owned by PolaStudio.

A Site Design covers design tokens, typography, visual rules, reusable component variants, templates, navigation/header/footer presentation, document and commerce presentation, assets/references, and responsive rules. It is visually editable, exportable/importable, duplicable and versionable.

Presentation authority does not imply database, filesystem, network, secret, administrator, publication or server-execution authority. Functional behavior that cannot be represented declaratively belongs to a constrained first-party component or Secure Extension with explicit capabilities.

The word `theme` may remain useful in migration or user-facing language, but it does not describe a privileged executable package in the PolaCore architecture.

## Real-world product requirements

`docs/PRODUCT_REQUIREMENTS.md` records a traceable first requirements batch derived from actual WordPress/WooCommerce usage. It maps recurring plugin/theme needs into PolaCore, PolaStudio, PolaCommerce and Secure Extensions, including structured content modeling, product options, unit-aware pricing, reorder, shipping zones, commercial documents, data portability, observability, navigation design, pedagogical custom behavior and custom theme migration.

These requirements are coverage targets and classification constraints. They are not evidence that the mechanisms have been implemented or validated.

## Current phase

The project is in architecture, adversarial review, and engineering-prototype phases. Security properties must be demonstrated before they are treated as platform guarantees.

The product architecture above is a durable direction, not authorization to build the UI, commerce stack, migration engine, or extension marketplace before the security substrate is credible.

## Product priorities

1. Establish a small, explicit trusted computing base.
2. Demonstrate isolation and authority boundaries with reproducible tests.
3. Prefer simple mechanisms whose effective behavior can be inspected.
4. Build a component execution model that remains safe under arbitrary component code execution.
5. Only after the security substrate is credible, build authoring, content, administration, migration, and ecosystem features on top of it.
6. Define stable structured-content, commerce, and extension contracts on top of the demonstrated security substrate.
7. Progressively implement PolaCore Studio, PolaCommerce, migration tooling, and the secure extension ecosystem.

## Non-goals for the current phase

- broad plugin compatibility;
- feature parity with WordPress;
- premature UI development;
- WordPress plugin or theme code compatibility;
- implicit broad authority for third-party extensions;
- page-builder compatibility as a design constraint;
- premature commerce implementation;
- speculative multi-backend abstractions without a demonstrated need;
- security claims based only on configuration or documentation.
