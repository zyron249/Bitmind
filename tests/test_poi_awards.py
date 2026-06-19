from fastapi.testclient import TestClient
from bitmind.api.main import app
from bitmind.core import models, rewards, ledger
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

@pytest.fixture
def client():
    return TestClient(app)


def test_award_and_reject_and_appeal_flow(client):
    # create users and task
    u1 = client.post("/users", json={"username": "alice"}).json()
    u2 = client.post("/users", json={"username": "bob"}).json()

    # boost u1 as validator
    user1 = models.get_user(u1["id"])
    user1.reputation = 0.9
    models.InMemoryDB.users[user1.id] = user1

    task = client.post("/tasks", json={"prompt":"What is 2+2?","answer_key":"4","is_test":True}).json()

    # evaluate submissions via POI endpoint
    r1 = client.post("/poi/evaluate", json={"user_id": u1["id"], "task_id": task["id"], "submission_content": "4"}).json()
    r2 = client.post("/poi/evaluate", json={"user_id": u2["id"], "task_id": task["id"], "submission_content": "four"}).json()

    # Try to award u1
    award_resp = client.post("/poi/award", json={"submission_id": r1["submission_id"], "approved_by_validator_id": u1["id"]})
    assert award_resp.status_code == 200
    ar = award_resp.json()
    assert ar["awarded"] is True
    assert ar["amount"] > 0

    # Prevent double awarding
    award_resp2 = client.post("/poi/award", json={"submission_id": r1["submission_id"], "approved_by_validator_id": u1["id"]})
    assert award_resp2.status_code == 200
    ar2 = award_resp2.json()
    assert ar2["awarded"] is False
    assert ar2["reason"] == "already_awarded"

    # Non-eligible cannot be awarded
    award_resp3 = client.post("/poi/award", json={"submission_id": r2["submission_id"], "approved_by_validator_id": u1["id"]})
    assert award_resp3.status_code == 200
    ar3 = award_resp3.json()
    assert ar3["awarded"] is False
    assert ar3["reason"] == "not_eligible"

    # Reject a submission
    rej = client.post("/poi/reject", json={"submission_id": r2["submission_id"], "validator_id": u1["id"], "reason": "low quality"})
    assert rej.status_code == 200
    jr = rej.json()
    assert jr["rejected"] is True

    # Create an appeal by u2
    appeal = client.post("/poi/appeal", json={"submission_id": r2["submission_id"], "user_id": u2["id"], "appeal_reason": "please recheck"})
    assert appeal.status_code == 200
    apr = appeal.json()
    assert apr["appeal_created"] is True

    # List appeals
    list_resp = client.get("/poi/appeals")
    assert list_resp.status_code == 200
    arr = list_resp.json()
    assert isinstance(arr, list)
    assert len(arr) == 1
    assert arr[0]["submission_id"] == r2["submission_id"]
