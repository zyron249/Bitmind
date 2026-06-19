import pytest
from fastapi.testclient import TestClient
from bitmind.api.main import app
from bitmind.core import models

from bitmind.core.models import InMemoryDB


@pytest.fixture(autouse=True)
def reset_db():
    # Reset in-memory DB before each test
    InMemoryDB.users = {}
    InMemoryDB.tasks = {}
    InMemoryDB.assignments = {}
    InMemoryDB.submissions = {}
    InMemoryDB.ledger_entries = []


@pytest.fixture
def client():
    return TestClient(app)


def test_create_user(client):
    res = client.post("/users", json={"username": "alice"})
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == "alice"
    assert "id" in data
    # check default balance
    assert data["balance"] == 100.0
