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


def test_batch_appeals_workflow(client):
    # create users and validator
    u1 = client.post("/users", json={"username": "alice"}).json()
    u2 = client.post("/users", json={"username": "bob"}).json()
    v = client.post("/validators", json={"user_id": u1["id"], "role": "validator"}).json()
    vid = v["validator_id"]
    client.post("/validators/stake", json={"validator_id": vid, "amount": 2000})

    # create task and submissions, then reject and appeal for both users
    task = client.post("/tasks", json={"prompt":"7+7","answer_key":"14","is_test":True}).json()
    ev1 = client.post("/poi/evaluate", json={"user_id": u1["id"], "task_id": task["id"], "submission_content": "fourteen"}).json()
    sid1 = ev1["submission_id"]
    client.post("/poi/reject", json={"submission_id": sid1, "validator_id": vid, "reason": "no"})
    ap1 = client.post("/poi/appeal", json={"submission_id": sid1, "user_id": u1["id"], "appeal_reason": "please"}).json()
    aid1 = ap1["appeal_id"]

    ev2 = client.post("/poi/evaluate", json={"user_id": u2["id"], "task_id": task["id"], "submission_content": "fourteen"}).json()
    sid2 = ev2["submission_id"]
    client.post("/poi/reject", json={"submission_id": sid2, "validator_id": vid, "reason": "no"})
    ap2 = client.post("/poi/appeal", json={"submission_id": sid2, "user_id": u2["id"], "appeal_reason": "please"}).json()
    aid2 = ap2["appeal_id"]

    # pending appeals
    pending = client.get("/poi/appeals/pending").json()
    pending_ids = [p["appeal_id"] for p in pending]
    assert aid1 in pending_ids and aid2 in pending_ids

    # batch approve
    resp = client.post("/poi/appeals/batch-approve", json={"validator_id": vid, "appeal_ids": [aid1, aid2], "reason": "batch"})
    assert resp.status_code == 200
    body = resp.json()
    assert aid1 in body["approved"] and aid2 in body["approved"]
    # audit events
    audits = client.get("/audit").json()
    types = [a["event_type"] for a in audits]
    assert types.count("appeal_approved") >= 2

    # try batch deny on same appeals (should be skipped)
    resp2 = client.post("/poi/appeals/batch-deny", json={"validator_id": vid, "appeal_ids": [aid1, aid2], "reason": "nope"})
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert len(body2["skipped"]) >= 2

    # inactive validator cannot batch approve
    client.post(f"/validators/{vid}/deactivate")
    resp3 = client.post("/poi/appeals/batch-approve", json={"validator_id": vid, "appeal_ids": [aid1], "reason": "x"})
    assert resp3.status_code == 403

    # inactive validator cannot batch deny
    resp4 = client.post("/poi/appeals/batch-deny", json={"validator_id": vid, "appeal_ids": [aid1], "reason": "x"})
    assert resp4.status_code == 403
