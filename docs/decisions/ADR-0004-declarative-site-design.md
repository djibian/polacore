# ADR-0004: Declarative Site Design replaces executable theme authority

## Status

Accepted product direction. Exact Site Design schema, styling surface and component model remain undecided and unproven.

## Context

WordPress themes commonly combine presentation, templates, assets and executable behavior. In practice, available themes are often broader or more opinionated than the site's actual needs, while custom themes are created to regain control.

That packaging also makes presentation an authority-bearing software unit: a theme can contain server-side and client-side code unrelated to visual design.

PolaCore needs whole-site design flexibility without making presentation itself a privileged runtime extension.

## Decision

PolaCore will not reproduce WordPress-style executable themes as a privileged application unit.

PolaStudio will own a declarative, versioned **Site Design** model that represents whole-site presentation, including at least:

- design tokens;
- typography and visual rules;
- reusable component variants;
- templates;
- navigation, header and footer presentation;
- content/document presentation;
- PolaCommerce presentation surfaces;
- assets/references;
- responsive rules.

A Site Design is data. It must be visually editable in PolaStudio, exportable/importable, duplicable and versionable.

Presentation authority does not imply database, filesystem, network, secret, administrator, publication or server-execution authority.

When a design needs functional behavior that cannot be represented declaratively, that behavior belongs to a constrained first-party component or Secure Extension with explicit capabilities. Advanced styling may be supported through a scoped, inspectable mechanism, but it does not gain server authority.

The term **theme** may remain in migration or user-facing language for familiarity, but it is not the canonical PolaCore authority model.

## Alternatives considered

### Reproduce WordPress themes

Rejected. It would reintroduce a package that mixes presentation and executable authority and would make PolaCore inherit compatibility constraints unrelated to its own product model.

### Make each site entirely custom code

Rejected as the default. It would make routine design changes unnecessarily developer-dependent and would undermine the goal of a powerful native authoring environment.

### Use a general-purpose page builder as the theme system

Rejected. Page-builder-style unrestricted layout composition does not provide the desired structured, reusable whole-site design model and tends to mix local page composition with global design concerns.

## Security implications

- Site Design documents must be schema-validatable without executing arbitrary theme code.
- Rendering must treat design/content values as data and apply explicit sanitization/escaping rules.
- Design imports must not silently acquire privileged capabilities.
- Custom assets and advanced styles require explicit validation and content-security handling.
- Functional components referenced by Site Design remain separately permissioned; design cannot widen their capabilities.
- Site Design version migrations must be deterministic and auditable.

## Evidence supporting the decision

This decision is grounded in repeated real-world difficulty finding WordPress themes that match the actual site need without excessive unrelated functionality, leading to custom theme development.

It is consistent with ADR-0001 (native structured editor/document model) and ADR-0003 (capability-based extensions): presentation should remain structurally editable while executable behavior remains separately constrained.

This ADR does not claim that the Site Design schema, renderer, CSS scoping model or component architecture has already been demonstrated.

## Consequences

- PolaStudio expands from page/content editor to whole-site design environment.
- Header, footer, navigation presentation, design tokens, templates and reusable component variants become first-party Studio responsibilities.
- Storefront-style footer customization and menu-icon plugins become unnecessary product categories.
- WordPress theme migration targets declarative Site Design semantics where recoverable.
- Executable behavior embedded in legacy themes must be classified separately and mapped to native components/extensions or reported unsupported.
- Site Design packages can become portable starting points without becoming privileged code bundles.

## Remaining uncertainty

- Exact Site Design schema and versioning strategy.
- Component/variant model and relationship to the canonical PolaCore document model.
- Responsive-authoring model.
- Advanced/scoped CSS or styling escape hatch.
- Asset packaging and supply-chain rules.
- How deterministic migration from common WordPress themes can be made.
- Whether some client-side interaction can remain declarative before requiring an extension.
