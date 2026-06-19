from fastapi.testclient import TestClient
from bitmind.api.main import app
from bitmind.core import models, audit, validators as core_validators
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


def test_appeal_resolution_and_permissions(client):
    # create users and validator
    u = client.post("/users", json={"username": "alice"}).json()
    v = client.post("/validators", json={"user_id": u["id"], "role": "validator"}).json()
    vid = v["validator_id"]
    # stake validator to activate
    client.post("/validators/stake", json={"validator_id": vid, "amount": 2000})

    # create task and submission then reject to create appeal
    task = client.post("/tasks", json={"prompt":"5+5","answer_key":"10","is_test":True}).json()
    ev = client.post("/poi/evaluate", json={"user_id": u["id"], "task_id": task["id"], "submission_content": "ten"}).json()
    sid = ev["submission_id"]
    # reject submission
    client.post("/poi/reject", json={"submission_id": sid, "validator_id": vid, "reason": "bad"})
    # create appeal
    ap = client.post("/poi/appeal", json={"submission_id": sid, "user_id": u["id"], "appeal_reason": "please"}).json()
    appeal_id = ap["appeal_id"]

    # active validator approves appeal
    resp = client.post(f"/poi/appeal/{appeal_id}/approve", json={"validator_id": vid})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "approved"
    # audit event exists
    audits = client.get("/audit").json()
    types = [a["event_type"] for a in audits]
    assert "appeal_approved" in types

    # create another appeal and test deny by active validator
    # reject again
    client.post("/poi/reject", json={"submission_id": sid, "validator_id": vid, "reason": "still"})
    ap2 = client.post("/poi/appeal", json={"submission_id": sid, "user_id": u["id"], "appeal_reason": "again"}).json()
    appeal_id2 = ap2["appeal_id"]
    resp2 = client.post(f"/poi/appeal/{appeal_id2}/deny", json={"validator_id": vid, "reason": "no"})
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "denied"
    audits2 = client.get("/audit").json()
    types2 = [a["event_type"] for a in audits2]
    assert "appeal_denied" in types2

    # inactive validator cannot approve
    client.post(f"/validators/{vid}/deactivate")
    resp3 = client.post(f"/poi/appeal/{appeal_id2}/approve", json={"validator_id": vid})
    assert resp3.status_code == 403

