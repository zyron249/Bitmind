from fastapi.testclient import TestClient
from bitmind.api.main import app
from bitmind.core import models, validators as core_validators, audit
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
    if hasattr(InMemoryDB, 'audit_events'):
        InMemoryDB.audit_events = {}
    if hasattr(InMemoryDB, 'proposals'):
        InMemoryDB.proposals = {}
    if hasattr(InMemoryDB, 'votes'):
        InMemoryDB.votes = {}

@pytest.fixture
def client():
    return TestClient(app)


def test_governance_proposal_and_voting(client):
    # create users
    u1 = client.post("/users", json={"username": "alice"}).json()
    u2 = client.post("/users", json={"username": "bob"}).json()
    # create validators and stake
    v1 = client.post("/validators", json={"user_id": u1["id"], "role": "validator"}).json()
    vid1 = v1["validator_id"]
    client.post("/validators/stake", json={"validator_id": vid1, "amount": 2000})
    v2 = client.post("/validators", json={"user_id": u2["id"], "role": "validator"}).json()
    vid2 = v2["validator_id"]
    client.post("/validators/stake", json={"validator_id": vid2, "amount": 1000})

    # create proposal
    p = client.post("/governance/proposals", json={"title": "Increase rewards", "description": "Test", "created_by": u1["id"]}).json()
    pid = p["proposal_id"]
    # list proposals
    plist = client.get("/governance/proposals").json()
    assert any(item["proposal_id"] == pid for item in plist)

    # vote: v1 yes, v2 no -> total active stake = 3000, yes =2000 -> >50% -> passes
    r1 = client.post("/governance/vote", json={"voter_validator_id": vid1, "proposal_id": pid, "vote": "yes"})
    assert r1.status_code == 200
    r2 = client.post("/governance/vote", json={"voter_validator_id": vid2, "proposal_id": pid, "vote": "no"})
    assert r2.status_code == 200

    # check proposal status
    pinfo = client.get(f"/governance/proposals/{pid}").json()
    assert pinfo["status"] == "passed"

    # audit events created for proposal creation and votes
    audits = client.get("/audit").json()
    types = [a["event_type"] for a in audits]
    assert "proposal_created" in types
    assert types.count("proposal_vote") >= 2

