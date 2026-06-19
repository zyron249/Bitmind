from fastapi.testclient import TestClient
from bitmind.api.main import app
from bitmind.core import models
from bitmind.core.models import InMemoryDB
from bitmind.consensus import slashing

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


def test_double_award_and_invalid_and_fraud_slash(client):
    # create users and validators
    u = client.post("/users", json={"username": "val1"}).json()
    v = client.post("/validators", json={"user_id": u["id"], "role": "validator"}).json()
    vid = v["validator_id"]
    client.post("/validators/stake", json={"validator_id": vid, "amount": 2000})

    # create task and evaluate
    task = client.post("/tasks", json={"prompt":"3+3","answer_key":"6","is_test":True}).json()
    ev = client.post("/poi/evaluate", json={"user_id": u["id"], "task_id": task["id"], "submission_content": "6"}).json()
    sid = ev["submission_id"]

    # first award should succeed
    r1 = client.post("/poi/award", json={"submission_id": sid, "approved_by_validator_id": vid})
    assert r1.status_code == 200
    assert r1.json()["awarded"] is True

    # double award attempt by same validator should trigger slashing and return already_awarded
    r2 = client.post("/poi/award", json={"submission_id": sid, "approved_by_validator_id": vid})
    assert r2.status_code == 200
    assert r2.json()["awarded"] is False

    # invalid validator action: validator exists but inactive -> simulate by deactivating and attempting award
    client.post(f"/validators/{vid}/deactivate")
    r3 = client.post("/poi/award", json={"submission_id": sid, "approved_by_validator_id": vid})
    assert r3.status_code == 403

    # fraudulent approval slashing: create a new submission with high fraud (we'll simulate by calling evaluate with fraud_risk high)
    ev2 = client.post("/poi/evaluate", json={"user_id": u["id"], "task_id": task["id"], "submission_content": "6", "fraud_risk": 0.95}).json()
    sid2 = ev2["submission_id"]
    # reactivate validator
    v2 = client.post("/validators", json={"user_id": u["id"], "role": "validator"}).json()
    vid2 = v2["validator_id"]
    client.post("/validators/stake", json={"validator_id": vid2, "amount": 2000})
    # attempt to award fraudulent submission -> should slash
    r4 = client.post("/poi/award", json={"submission_id": sid2, "approved_by_validator_id": vid2})
    assert r4.status_code == 200
    assert r4.json()["awarded"] is False or r4.json()["reason"] in ("not_eligible","awarded")
    # confirm slash recorded
    info = client.get(f"/validators/{vid2}").json()
    assert info["slashes_count"] >= 1

