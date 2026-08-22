# ADR-0001: Native structured editor and PolaCore-owned document model

## Status

Accepted product direction. Implementation mechanism remains undecided and unproven.

## Context

PolaCore needs a modern authoring experience capable of replacing the common WordPress editing workflow without inheriting page-builder complexity or making WordPress/Gutenberg storage constraints part of the new platform.

A visual editor is a core product capability, but the persisted content model must remain stable independently of any editor framework.

## Decision

PolaCore will provide a first-party editor, **PolaCore Studio**.

The canonical persisted representation will be a PolaCore-owned, typed, versioned structured document/tree model. Rendered HTML is an output, not the source of truth.

The model should be able to evolve toward structured text, reusable components, semantic layout, responsive intent, design tokens, dynamic data bindings, forms, and other native capabilities while remaining validatable independently of rendering code.

PolaCore Studio should offer direct visual editing and powerful composition while preserving semantic structure. Unrestricted page-builder-style presentation nesting is not the target interaction model.

Rich-text engines such as ProseMirror/Tiptap or Lexical may be evaluated for editing subtrees. Any selected library must remain an implementation component rather than the persistence authority.

## Alternatives considered

### Adopt Gutenberg as the PolaCore editor

Rejected as the long-term architecture. Gutenberg remains valuable as a reference implementation and migration source, but PolaCore should not inherit WordPress-specific persistence and compatibility constraints.

### Use a general-purpose page builder

Rejected. It would weaken structural guarantees, increase migration/rendering complexity, and make authoring overly dependent on presentation markup.

### Build every text-editing primitive from scratch

Not selected. Mature editor engines may reduce implementation risk for rich-text behavior, selection, input methods, accessibility, history, and collaboration.

## Security implications

- Persisted documents must be schema-validatable without executing editor extensions.
- Editor extensions must not implicitly receive CMS-wide authority.
- Rendering must treat document data as data, with explicit sanitization and capability boundaries for dynamic behavior.
- Version migrations of the document schema must be deterministic and auditable.

## Evidence supporting the decision

The decision is a product/architecture constraint authorized by the project owner. It does not assert that a specific editor engine or document schema has yet been demonstrated.

WordPress/Gutenberg is retained as an interoperability reference because its blocks are manipulated as structured data in memory but commonly serialized back into `post_content`; PolaCore is free to make the structured representation canonical from the beginning.

## Consequences

- A dedicated document schema/versioning design becomes a future foundational task.
- Editor-engine selection must be evaluated against PolaCore's model rather than defining it.
- WordPress/Gutenberg migration requires a translation layer into the PolaCore document model.
- Front-end renderers and future alternative outputs consume the same canonical document representation.

## Remaining uncertainty

- Exact document schema and versioning rules.
- ProseMirror/Tiptap vs Lexical vs another editor substrate.
- Collaboration architecture.
- Exact boundaries between document nodes, application components, forms, and dynamic data.
- Accessibility and responsive-authoring interaction design.
