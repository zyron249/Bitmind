from fastapi.testclient import TestClient
from bitmind.api.main import app
from bitmind.core import models, validators as core_validators
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
    if hasattr(InMemoryDB, 'proposals'):
        InMemoryDB.proposals = {}
    if hasattr(InMemoryDB, 'votes'):
        InMemoryDB.votes = {}

@pytest.fixture
def client():
    return TestClient(app)


def test_voting_periods_and_quorum(client):
    # create validators and stake
    u1 = client.post("/users", json={"username": "val1"}).json()
    u2 = client.post("/users", json={"username": "val2"}).json()
    v1 = client.post("/validators", json={"user_id": u1["id"], "role": "validator"}).json()
    vid1 = v1["validator_id"]
    client.post("/validators/stake", json={"validator_id": vid1, "amount": 2000})
    v2 = client.post("/validators", json={"user_id": u2["id"], "role": "validator"}).json()
    vid2 = v2["validator_id"]
    client.post("/validators/stake", json={"validator_id": vid2, "amount": 1000})

    now = datetime.utcnow()
    start = (now + timedelta(seconds=10)).isoformat()
    end = (now + timedelta(seconds=20)).isoformat()

    # create proposal with future start
    p = client.post("/governance/proposals", json={"title":"Time Test","description":"","created_by":u1["id"], "voting_starts_at": start, "voting_period_seconds": 5, "quorum_required": 0.2}).json()
    pid = p["proposal_id"]

    # cannot vote before start
    r = client.post("/governance/vote", json={"voter_validator_id": vid1, "proposal_id": pid, "vote": "yes"})
    assert r.status_code == 400

    # create a proposal with immediate start but short period
    p2 = client.post("/governance/proposals", json={"title":"Short","description":"","created_by":u1["id"], "voting_period_seconds": 1, "quorum_required": 0.2}).json()
    pid2 = p2["proposal_id"]
    # vote within period
    r2 = client.post("/governance/vote", json={"voter_validator_id": vid1, "proposal_id": pid2, "vote": "yes"})
    assert r2.status_code == 200
    # wait past period (simulate by adjusting proposal end)
    prop = client.get(f"/governance/proposals/{pid2}").json()
    # simulate end by setting voting_ends_at to past
    from bitmind.core import models as core_models
    core_models.InMemoryDB.proposals[pid2].voting_ends_at = datetime.utcnow() - timedelta(seconds=1)

    # cannot vote after end
    r3 = client.post("/governance/vote", json={"voter_validator_id": vid2, "proposal_id": pid2, "vote": "no"})
    assert r3.status_code == 400

    # finalize without quorum: only 2000 cast / total 3000 -> quorum 0.666 > required 0.2 actually met. To test quorum not met, create proposal with higher quorum
    p3 = client.post("/governance/proposals", json={"title":"High Quorum","description":"","created_by":u1["id"], "voting_period_seconds": 1, "quorum_required": 0.9}).json()
    pid3 = p3["proposal_id"]
    # cast a single small vote
    client.post("/governance/vote", json={"voter_validator_id": vid1, "proposal_id": pid3, "vote": "yes"})
    # simulate end
    core_models.InMemoryDB.proposals[pid3].voting_ends_at = datetime.utcnow() - timedelta(seconds=1)
    res = client.post(f"/governance/proposals/{pid3}/finalize")
    assert res.status_code == 200
    assert res.json()["status"] == "rejected"

    # finalization passes when quorum and yes majority met
    p4 = client.post("/governance/proposals", json={"title":"Pass Test","description":"","created_by":u1["id"], "voting_period_seconds": 1, "quorum_required": 0.2}).json()
    pid4 = p4["proposal_id"]
    client.post("/governance/vote", json={"voter_validator_id": vid1, "proposal_id": pid4, "vote": "yes"})
    client.post("/governance/vote", json={"voter_validator_id": vid2, "proposal_id": pid4, "vote": "no"})
    # simulate end
    core_models.InMemoryDB.proposals[pid4].voting_ends_at = datetime.utcnow() - timedelta(seconds=1)
    res2 = client.post(f"/governance/proposals/{pid4}/finalize")
    assert res2.status_code == 200
    assert res2.json()["status"] == "passed"

    # audit event created on finalize
    audits = client.get("/audit").json()
    types = [a["event_type"] for a in audits]
    assert "proposal_finalized" in types
