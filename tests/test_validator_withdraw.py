from fastapi.testclient import TestClient
from bitmind.api.main import app
from bitmind.core import models, validators as core_validators
from bitmind.core.models import InMemoryDB

import pytest
from datetime import datetime, timedelta

@pytest.fixture(autouse=True)
def reset_db():
    InMemoryDB.users = {}
    InMemoryDB.tasks = {}
    InMemoryDB.assignments = {}
    InMemoryDB.submissions = {}
    InMemoryDB.ledger_entries = []
    InMemoryDB.appeals = []
    InMemoryDB.rejections = []
    if hasattr(InMemoryDB, 'validators'):
        InMemoryDB.validators = {}
    if hasattr(InMemoryDB, 'audit_events'):
        InMemoryDB.audit_events = {}

@pytest.fixture
def client():
    return TestClient(app)


def test_validator_withdraw_flow(client):
    u = client.post("/users", json={"username": "valwithdraw"}).json()
    v = client.post("/validators", json={"user_id": u["id"], "role": "validator"}).json()
    vid = v["validator_id"]
    # stake to enable
    client.post("/validators/stake", json={"validator_id": vid, "amount": 2000})
    # initiate unstake
    client.post("/validators/unstake", json={"validator_id": vid})
    # cannot withdraw immediately
    w1 = client.post("/validators/withdraw", json={"validator_id": vid})
    assert w1.status_code == 400
    # simulate cooldown passed by setting unstake_cooldown_end to past
    validator_obj = core_validators.get_validator(vid)
    validator_obj.unstake_cooldown_end = datetime.utcnow() - timedelta(days=1)
    core_validators._ensure_registry()
    # now withdraw
    w2 = client.post("/validators/withdraw", json={"validator_id": vid})
    assert w2.status_code == 200
    body = w2.json()
    assert body["withdrawn"] is True
    # audit event created
    audits = client.get("/audit").json()
    types = [a["event_type"] for a in audits]
    assert "withdraw" in types
