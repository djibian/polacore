# PolaCore

PolaCore is an experimental secure CMS and component platform designed around least authority, strong isolation, explicit capabilities, and verifiable security invariants.

The project is currently in architecture, adversarial review, and engineering-prototype phases.

## Core goal

A fully compromised third-party component must not be able to compromise the CMS authority, create or promote administrators, publish without authorization, read secrets or unauthorized data, compromise other components, gain ambient network/filesystem/database authority, or establish persistence.

## Long-term product direction

PolaCore is intended to cover the important uses of WordPress without reproducing its historical authority model.

Its product architecture is organized around:

- **PolaCore Kernel** — a deliberately small trusted CMS core;
- **PolaCore Studio** — a native modern visual editor backed by a PolaCore-owned typed and versioned document model;
- **PolaCommerce** — an official first-party commerce module outside the minimal kernel;
- **Secure Extensions** — explicit capabilities and isolated execution instead of implicit broad plugin access;
- **WordPress/WooCommerce migration** — semantic translation into native PolaCore concepts rather than runtime compatibility with arbitrary legacy plugins/themes.

These are durable product boundaries, not a change to the current sequencing: the security substrate is being demonstrated before authoring, commerce, migration, and ecosystem features are implemented.

See `docs/PRODUCT.md`, `docs/ARCHITECTURE.md`, and `docs/decisions/` on the engineering line for the detailed direction.

## Development model

Architecture, engineering, and red-team work evolve together. Security claims should be backed by primary sources, reproducible tests, or explicit formal reasoning, and unproven assumptions should remain identified as such.

The repository will progressively host the executable prototypes, security tests, implementation decisions, migration tooling, and eventually the CMS itself.
