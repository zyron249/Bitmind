from fastapi.testclient import TestClient
from bitmind.api.main import app
from bitmind.core import models, validators as core_validators
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


def test_stake_and_unstake_and_ranking(client):
    # create user and validator
    u = client.post("/users", json={"username": "valuser"}).json()
    v = client.post("/validators", json={"user_id": u["id"], "role": "validator"}).json()
    vid = v["validator_id"]

    # cannot be active until stake >= 1000
    info = client.get(f"/validators/{vid}").json()
    assert info["active"] is False

    # stake insufficient amount
    stake_resp = client.post("/validators/stake", json={"validator_id": vid, "amount": 100.0})
    assert stake_resp.status_code == 200
    info2 = client.get(f"/validators/{vid}").json()
    assert info2["staked_amount"] == 100.0
    assert info2["active"] is False

    # stake to reach minimum
    stake_resp2 = client.post("/validators/stake", json={"validator_id": vid, "amount": 1000.0})
    assert stake_resp2.status_code == 200
    info3 = client.get(f"/validators/{vid}").json()
    assert info3["staked_amount"] >= 1100.0
    assert info3["active"] is True

    # initiate unstake
    unstake_resp = client.post("/validators/unstake", json={"validator_id": vid})
    assert unstake_resp.status_code == 200
    uinfo = client.get(f"/validators/{vid}").json()
    assert uinfo["active"] is False
    assert uinfo["unstake_cooldown_end"] is not None

    # ranking endpoint returns validators
    rank = client.get("/validators/ranking")
    assert rank.status_code == 200
    arr = rank.json()
    assert isinstance(arr, list)
    assert len(arr) >= 1

