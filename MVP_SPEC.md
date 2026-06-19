# MVP Specification

This document provides the MVP endpoints, models, and core flow to implement BitMind's first working prototype.

Core Entities

- User
  - id, username, reputation, balance, staked_amount

- Task
  - id, prompt, optional answer_key (for hidden-test tasks), difficulty, is_test_flag

- Assignment
  - id, task_id, assignee_user_id, status: [assigned, submitted, graded]

- Submission
  - id, assignment_id, user_id, content, auto_score, human_score, final_score, verdict

- LedgerEntry
  - tx_id, user_id, amount, reason, timestamp

Endpoints (example)

- POST /users
  - Create a user

- POST /tasks
  - Create a task (can be a hidden test if answer_key provided and is_test_flag=true)

- POST /tasks/{task_id}/assign
  - Assign task to N reviewers (3–7)

- POST /assignments/{assignment_id}/submit
  - Submit an answer for assignment

- POST /users/{user_id}/stake
  - Stake BMD for anti-sybil and slashing

- GET /ledger/{user_id}
  - View simulated ledger and balance

Core Flows

1. Create task (optionally a hidden test)
2. Assign to multiple users
3. Users submit answers
4. For each submission:
   - Run AI-scoring placeholder -> auto_score
   - If task is hidden-test, check against answer_key -> fail/pass
   - Compute fraud_risk_score using heuristics
   - Store submission, update assignment status
5. When required number of submissions collected for a task, compute consensus (placeholder): average/majority rules
6. Final scoring leads to reputation update and reward distribution via simulated ledger
7. If fraud detected -> apply slashing (stake burn) and ledger correction

Reputation & Reward

- Reputation is a moving average (alpha parameter) updated with final_score
- Reward = base_reward * final_score * f(reputation) where f is a simple multiplier
- Stake is required for higher-volume contributors or for validator roles (simulated)

AI Integration

- A placeholder function exists for AI scoring. API integration (e.g. OpenAI) will be added later via environment variables, e.g. OPENAI_API_KEY.

Testing

- Use unit tests to simulate honest and malicious contributors
- Validate hidden-test detection, consensus, reward distribution, and slashing

