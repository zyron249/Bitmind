from fastapi.testclient import TestClient
from bitmind.api.main import app
from bitmind.core import models, rewards, ledger, validators as core_validators
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

@pytest.fixture
def client():
    return TestClient(app)


def test_validators_and_permission_flow(client):
    # create users and task
    u1 = client.post("/users", json={"username": "alice"}).json()
    u2 = client.post("/users", json={"username": "bob"}).json()

    # create a validator for u1 via API
    v = client.post("/validators", json={"user_id": u1["id"], "role": "validator"})
    assert v.status_code == 201
    vj = v.json()
    vid = vj["validator_id"]

    # create task and evaluate
    task = client.post("/tasks", json={"prompt":"What is 2+2?","answer_key":"4","is_test":True}).json()
    r1 = client.post("/poi/evaluate", json={"user_id": u1["id"], "task_id": task["id"], "submission_content": "4"}).json()

    # active validator can award
    award_resp = client.post("/poi/award", json={"submission_id": r1["submission_id"], "approved_by_validator_id": vid})
    assert award_resp.status_code == 200
    ar = award_resp.json()
    assert ar["awarded"] is True

    # deactivate validator
    deact = client.post(f"/validators/{vid}/deactivate")
    assert deact.status_code == 200

    # create another submission
    r2 = client.post("/poi/evaluate", json={"user_id": u2["id"], "task_id": task["id"], "submission_content": "four"}).json()

    # inactive validator cannot award
    award_resp2 = client.post("/poi/award", json={"submission_id": r2["submission_id"], "approved_by_validator_id": vid})
    assert award_resp2.status_code == 403

    # non-existing validator cannot award
    award_resp3 = client.post("/poi/award", json={"submission_id": r2["submission_id"], "approved_by_validator_id": "nonexistent"})
    assert award_resp3.status_code == 403

    # active validator (re-create) can reject
    v2 = client.post("/validators", json={"user_id": u1["id"], "role": "validator"})
    vid2 = v2.json()["validator_id"]
    rej = client.post("/poi/reject", json={"submission_id": r2["submission_id"], "validator_id": vid2, "reason": "low quality"})
    assert rej.status_code == 200
    jr = rej.json()
    assert jr["rejected"] is True
