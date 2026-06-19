# BitMind Architecture

This document summarizes high-level components and responsibilities for the BitMind MVP.

Components

- API (FastAPI)
  - Public REST endpoints for users, tasks, assignments, submissions, staking, and admin actions.

- Core services (Python modules)
  - tasks: Task lifecycle, assignment creation, hidden-test injection
  - reputation: Reputation calculation and decay
  - rewards: Reward calculation and distribution using a simulated ledger
  - anti_cheat: Hidden-test evaluation, fraud risk heuristics, AI-scoring placeholder
  - ledger: In-memory ledger of BMD balances and transactions
  - models: Pydantic and in-memory DB models

- Storage
  - MVP uses in-memory Python dictionaries (InMemoryDB). Replaceable with PostgreSQL in later stages.

- External integrations (future)
  - OpenAI (AI scoring and augmentation) — placeholder hooks using environment variables
  - Persistent DB (Postgres)
  - Optional KYC providers
  - On-chain token / smart contracts for BMD (future)

Security & Anti-cheat design

- Hidden tests: Tasks may include hidden/known answers. These are mixed into the assignment stream to validate contributors without revealing tests.
- Multi-review consensus: Each non-test task is assigned to multiple contributors; the system aggregates reviews and applies consensus rules.
- Reputation: Reputation grows/shrinks with validated quality; it affects reward weight and validator eligibility.
- Stake & slashing: Contributors can stake BMD; proven fraud leads to slashing simulated by the rewards/ledger module.
- Fraud heuristics: Device fingerprinting, behavioral signals, rapid identical answers, and hidden test failures contribute to fraud risk scoring (placeholders).

Notes

- MVP intentionally focuses on the anti-cheat & reward architecture rather than blockchain. A simulated ledger provides internal consistency for rewards and stakes; migrating ledger operations on-chain is a later step.
