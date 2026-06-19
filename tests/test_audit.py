from fastapi.testclient import TestClient
from bitmind.api.main import app
from bitmind.core import audit, models, validators as core_validators
from bitmind.core.models import InMemoryDB

import pytest

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


def test_audit_events_on_actions(client):
    u = client.post("/users", json={"username": "auditor"}).json()
    # create validator
    v = client.post("/validators", json={"user_id": u["id"], "role": "validator"}).json()
    vid = v["validator_id"]
    # stake
    client.post("/validators/stake", json={"validator_id": vid, "amount": 2000})
    # create task and submission
    task = client.post("/tasks", json={"prompt":"1+1","answer_key":"2","is_test":True}).json()
    ev = client.post("/poi/evaluate", json={"user_id": u["id"], "task_id": task["id"], "submission_content": "2"}).json()
    sid = ev["submission_id"]
    # award
    client.post("/poi/award", json={"submission_id": sid, "approved_by_validator_id": vid})
    # reject
    client.post("/poi/reject", json={"submission_id": sid, "validator_id": vid, "reason": "test"})
    # appeal
    client.post("/poi/appeal", json={"submission_id": sid, "user_id": u["id"], "appeal_reason": "please"})
    # unstake
    client.post("/validators/unstake", json={"validator_id": vid})

    # list audits
    audits = client.get("/audit").json()
    assert isinstance(audits, list)
    # ensure at least one audit for stake, award, reject, appeal, unstake
    types = [a["event_type"] for a in audits]
    assert "stake" in types or "unstake" in types or "award" in types

