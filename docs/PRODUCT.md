# PolaCore Product

## Purpose

PolaCore is an experimental secure CMS and component platform designed around least authority, strong isolation, explicit capabilities, and verifiable security invariants.

The project is not a WordPress hardening fork. WordPress may be used as a migration source, compatibility reference, or benchmark, but it is not the authority model for PolaCore.

## Product direction

PolaCore aims to cover the important uses of WordPress without reproducing its historical architecture.

The long-term product has four first-class layers:

1. **PolaCore Kernel** — the smallest practical trusted CMS core for identity, authorization, content, media, publication, versioning, and stable APIs.
2. **PolaCore Studio** — a first-party modern visual editor built around a typed and versioned structured-content model rather than page-builder markup or HTML as the canonical source.
3. **PolaCommerce** — an official first-party commerce module, deeply integrated with PolaCore but separable from the minimal kernel.
4. **Secure Extensions** — an extension ecosystem based on explicit capabilities, stable APIs, least authority, and isolation rather than implicit broad access.

A strategic fifth capability is the **WordPress/WooCommerce migration system**, which translates sites into native PolaCore concepts instead of importing legacy executable components.

## Core product promise

A third-party component must remain constrained to the authority explicitly granted to it. Installing a component must not implicitly grant access to CMS administration, publication, secrets, unrelated components, storage, or network resources.

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

## Current phase

The project is in architecture, adversarial review, and engineering-prototype phases. Security properties must be demonstrated before they are treated as platform guarantees.

The product architecture above is a durable direction, not authorization to build the UI, commerce stack, migration engine, or extension marketplace before the security substrate is credible.

## Product priorities

1. Establish a small, explicit trusted computing base.
2. Demonstrate isolation and authority boundaries with reproducible tests.
3. Prefer simple mechanisms whose effective behavior can be inspected.
4. Build a component execution model that preserves explicit authority boundaries.
5. Define stable structured-content, authoring, commerce, extension, and migration contracts on top of the demonstrated security substrate.
6. Progressively implement PolaCore Studio, PolaCommerce, migration tooling, and the secure extension ecosystem.

## Non-goals for the current phase

- WordPress plugin or theme code compatibility;
- implicit broad authority for third-party extensions;
- page-builder compatibility as a design constraint;
- feature parity with every WordPress plugin;
- premature UI or commerce implementation;
- speculative multi-backend abstractions without a demonstrated need;
- security claims based only on configuration or documentation.
