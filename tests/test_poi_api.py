from fastapi.testclient import TestClient
from bitmind.api.main import app
from bitmind.core import models, rewards
from bitmind.core.models import InMemoryDB

import pytest

@pytest.fixture(autouse=True)
def reset_db():
    InMemoryDB.users = {}
    InMemoryDB.tasks = {}
    InMemoryDB.assignments = {}
    InMemoryDB.submissions = {}
    InMemoryDB.ledger_entries = []

@pytest.fixture
def client():
    return TestClient(app)


def test_poi_api_evaluate_and_status(client):
    # create users and task
    u1 = client.post("/users", json={"username": "alice"}).json()
    u2 = client.post("/users", json={"username": "bob"}).json()
    u3 = client.post("/users", json={"username": "carol"}).json()

    # boost u1 as validator
    client_user = models.get_user(u1["id"])
    client_user.reputation = 0.9
    models.InMemoryDB.users[client_user.id] = client_user

    task = client.post("/tasks", json={"prompt":"What is 1+1?","answer_key":"2","is_test":True}).json()

    # evaluate submissions via POI endpoint
    res1 = client.post("/poi/evaluate", json={"user_id": u1["id"], "task_id": task["id"], "submission_content": "2"})
    res2 = client.post("/poi/evaluate", json={"user_id": u2["id"], "task_id": task["id"], "submission_content": "2"})
    res3 = client.post("/poi/evaluate", json={"user_id": u3["id"], "task_id": task["id"], "submission_content": "two"})

    assert res1.status_code == 200
    j1 = res1.json()
    assert "final_score" in j1
    assert "reward_eligible" in j1

    # status endpoint
    status = client.get(f"/poi/status/{j1['submission_id']}")
    assert status.status_code == 200
    s = status.json()
    assert s["final_score"] == j1["final_score"]

    # list evaluations
    list_resp = client.get("/poi/evaluations")
    assert list_resp.status_code == 200
    arr = list_resp.json()
    assert isinstance(arr, list)
    assert len(arr) == 3

    # check reward amounts for eligible ones
    eligible = [a for a in arr if a["reward_eligible"]]
    assert len(eligible) >= 1
