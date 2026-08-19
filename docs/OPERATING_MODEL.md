# PolaCore Operating Model

- **ChatGPT Governance task**: one scheduled task with two strictly separated modes: Lead & Architecture and Security Lab.
- **Codex Experimenter**: resolves high-value uncertainty with small reproducible experiments.
- **Codex Builder**: implements governance-approved bounded increments.
- **Codex Adversary**: independently tries to falsify security claims.
- **Codex Reviewer**: independently audits implementation, evidence, TCB, and test quality.
- **GitHub**: shared memory and work queue.
- **GitHub Actions**: mechanical execution of positive and adversarial tests.
- **Emmanuel**: explicit authority for durable product choices that cannot be decided technically and all promotion to `main`.

Normal technical integration targets `engineering`; no autonomous actor writes to `main`.
