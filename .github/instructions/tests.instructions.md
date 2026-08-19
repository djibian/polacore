---
applyTo: "tests/**,.github/workflows/**,docs/security/*EVIDENCE*.md"
---

# Test and evidence instructions

- A test is evidence only for the exact property it exercises.
- Prefer the smallest regression that would have failed before the fix.
- Require adversarial/negative tests for security boundaries where practical.
- Flag tests whose success depends on a synthetic marker while the claim concerns real runtime or user-visible behavior.
- Flag assertions weakened to accommodate implementation behavior.
- Keep `SKIP`, unavailable privilege, or missing fixtures visible and classify the corresponding property as `UNPROVEN`.
- Check that cleanup/lifecycle behavior cannot accidentally make a test pass.
- Distinguish `PROVEN_BY_TEST`, `VERIFIED_BY_CI`, `VERIFIED_BY_CODE_INSPECTION`, inference, and remaining uncertainty.
- Green CI never upgrades a claim beyond the oracle exercised by that CI.
