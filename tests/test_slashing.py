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

@pytest.fixture
def client():
    return TestClient(app)


def test_slashing_behavior(client):
    u = client.post("/users", json={"username": "badval"}).json()
    v = client.post("/validators", json={"user_id": u["id"], "role": "validator"}).json()
    vid = v["validator_id"]

    # stake to enable
    client.post("/validators/stake", json={"validator_id": vid, "amount": 1500})
    info = client.get(f"/validators/{vid}").json()
    staked_before = info["staked_amount"]

    # apply fraud slashing
    slashed = slashing.slash_validator_for_event(vid, "fraud_approval")
    assert slashed > 0
    info2 = client.get(f"/validators/{vid}").json()
    assert info2["slashes_count"] >= 1
    assert info2["staked_amount"] <= staked_before

    # apply double award slashing
    slashed2 = slashing.slash_validator_for_event(vid, "double_award")
    assert slashed2 > 0
    info3 = client.get(f"/validators/{vid}").json()
    assert info3["slashes_count"] >= 2
