import pytest
from fastapi.testclient import TestClient
from bitmind.api.main import app
from bitmind.core import models, rewards

from bitmind.core.models import InMemoryDB

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


def test_hidden_test_flow(client):
    # create users
    u1 = client.post("/users", json={"username": "u1"}).json()
    u2 = client.post("/users", json={"username": "u2"}).json()
    u3 = client.post("/users", json={"username": "u3"}).json()

    # create hidden test task
    task = client.post("/tasks", json={"prompt": "What is 2+2?","answer_key":"4","difficulty":1,"is_test":True}).json()

    # assign to 3 users
    resp = client.post(f"/tasks/{task['id']}/assign", json={"assignees": [u1['id'], u2['id'], u3['id']]})
    assert resp.status_code == 200
    assignments = resp.json()["assignments"]
    assert len(assignments) == 3

    # submit answers: two correct, one wrong
    # find assignment ids
    a1 = assignments[0]["id"]
    a2 = assignments[1]["id"]
    a3 = assignments[2]["id"]

    r1 = client.post(f"/assignments/{a1}/submit", json={"content": "4"})
    r2 = client.post(f"/assignments/{a2}/submit", json={"content": "4"})
    r3 = client.post(f"/assignments/{a3}/submit", json={"content": "five"})

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 200

    j1 = r1.json()
    j2 = r2.json()
    j3 = r3.json()

    assert j1["hidden_test_passed"] is True
    assert j2["hidden_test_passed"] is True
    assert j3["hidden_test_passed"] is False

    # reward distribution should have credited u1 and u2
    ledger1 = client.get(f"/ledger/{u1['id']}").json()
    ledger2 = client.get(f"/ledger/{u2['id']}").json()
    ledger3 = client.get(f"/ledger/{u3['id']}").json()

    # balances changed for winners
    assert ledger1["balance"] > 100.0
    assert ledger2["balance"] > 100.0
    # loser likely unchanged
    assert ledger3["balance"] <= 100.0
