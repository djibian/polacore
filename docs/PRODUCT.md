# PolaCore Product

## Purpose

PolaCore is an experimental secure CMS and component platform designed around least authority, strong isolation, explicit capabilities, and verifiable security invariants.

The project is not a WordPress hardening fork. WordPress may be used as a migration appliance, compatibility source, or adversarial benchmark, but it is not the authority model for PolaCore.

## Core product promise

A third-party component may be fully compromised without thereby obtaining authority over the CMS core, administrators, publication, secrets, unrelated components, ambient storage, arbitrary network access, or durable persistence.

## Current phase

The project is in architecture, adversarial review, and engineering-prototype phases. Security properties must be demonstrated before they are treated as platform guarantees.

## Product priorities

1. Establish a small, explicit trusted computing base.
2. Demonstrate isolation and authority boundaries with reproducible tests.
3. Prefer simple mechanisms whose effective behavior can be inspected.
4. Build a component execution model that remains safe under arbitrary component code execution.
5. Only after the security substrate is credible, build authoring, content, administration, migration, and ecosystem features on top of it.

## Non-goals for the current phase

- broad plugin compatibility;
- feature parity with WordPress;
- premature UI development;
- speculative multi-backend abstractions without a demonstrated need;
- security claims based only on configuration or documentation.
