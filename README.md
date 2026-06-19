# BitMind

![CI](https://github.com/zyron249/Bitmind/actions/workflows/ci.yml/badge.svg)

BitMind is a prototype project that demonstrates a quality-first reward system for human contributions backed by a simulated token ledger (BMD). The focus is on anti-cheat, reputation, multi-review consensus, and reward distribution. This MVP is intentionally in-memory and does not include any blockchain or real OpenAI keys.

Features (MVP)
- User creation and basic wallet (simulated)
- Create AI training tasks and hidden test tasks
- Assign tasks to multiple users (3–7 reviewers)
- Submit answers and automatic placeholder AI scoring
- Hidden test checking
- Multi-review consensus placeholder
- Reputation update
- Simulated BMD reward ledger and stake/slashing simulation
- Fraud risk scoring (heuristic placeholder)
- REST API with FastAPI

Run locally (development):
1. Create a Python 3.10+ virtual environment
2. pip install -r requirements.txt
3. uvicorn bitmind.api.main:app --reload --port 8000

OpenAPI docs: http://127.0.0.1:8000/docs

Testing

- Run unit tests:
  pytest -q

Coverage

- Run coverage report:
  make coverage

Docker (development)

- Build and run with Docker Compose (starts API, Postgres, Redis):
  make docker-up

CI (GitHub Actions)

- The repository includes a CI workflow (.github/workflows/ci.yml) that runs on push and pull requests to main. The workflow:
  - Installs dependencies
  - Runs ruff linter (must pass)
  - Runs pytest with coverage reporting (must pass)

Notes

- This project is an MVP for architecture and experimentation. Do NOT use it in production.
- No real OpenAI API key is included; integration points are clearly marked to be added via environment variables later.
- The MVP uses an in-memory storage backend by default. A PostgreSQL scaffold exists in bitmind/db/ for future migration and Alembic usage.
