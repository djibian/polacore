# First Codex Run

## Experimenter target

Branch: `codex/experiment/p117-staging-traversal`

Role: Experimenter

Objective: establish the smallest reproducible fd-relative traversal experiment for P117 (`SourceTraversalCannotEscapeStaging`).

The experiment must read `AGENTS.md` and the active GitHub work issue before modifying code.

It should prefer an isolated experiment/harness over premature production architecture and must report:

- exact hypothesis;
- tested Linux primitives and flags;
- attack cases exercised;
- observed results;
- environment/kernel limitations;
- what remains unproven;
- whether the proposed primitive is suitable for later Builder work.

## Independent attack target

Branch: `codex/test/p117-staging-attacks`

Role: Adversary/Test author after an implementation or experiment exists to attack.

Do not start by copying the Experimenter's reasoning. Read the invariant and resulting code/evidence, then construct independent attempts to escape staging or create false-positive validation.
