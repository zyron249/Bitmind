from fastapi.testclient import TestClient
from bitmind.api.main import app
from bitmind.core import models, audit
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
    if hasattr(InMemoryDB, 'blocks'):
        InMemoryDB.blocks = []

@pytest.fixture
def client():
    return TestClient(app)


def test_explorer_pagination_and_filters(client):
    # create users and validators
    u1 = client.post("/users", json={"username": "alice"}).json()
    u2 = client.post("/users", json={"username": "bob"}).json()
    v1 = client.post("/validators", json={"user_id": u1["id"], "role": "validator"}).json()
    v2 = client.post("/validators", json={"user_id": u2["id"], "role": "admin"}).json()
    vid1 = v1["validator_id"]
    vid2 = v2["validator_id"]
    client.post("/validators/stake", json={"validator_id": vid1, "amount": 2000})
    client.post("/validators/stake", json={"validator_id": vid2, "amount": 1500})

    # create blocks with transactions
    from bitmind.core import models as core_models
    blocks = []
    for i in range(5):
        txs = []
        for j in range(3):
            txs.append({"txid": f"tx{i}{j}", "from": "alice" if j % 2 == 0 else "bob", "to": "carol" if j % 2 == 0 else "dave", "amount": i * 10 + j})
        blocks.append({"index": i, "hash": f"h{i}", "transactions": txs})
    core_models.InMemoryDB.blocks = blocks

    # create audit events
    from bitmind.core import audit as core_audit
    core_audit.add_audit_event(event_type="evA", actor_id=u1["id"], target_id="t1")
    core_audit.add_audit_event(event_type="evB", actor_id=u2["id"], target_id="t2")
    core_audit.add_audit_event(event_type="evA", actor_id=u1["id"], target_id="t3")

    # create proposals
    client.post("/governance/proposals", json={"title":"P1","description":"","created_by":u1["id"]})
    p2 = client.post("/governance/proposals", json={"title":"P2","description":"","created_by":u2["id"]}).json()
    pid2 = p2["proposal_id"]
    # set status of p2 to passed
    from bitmind.governance import proposals as gov_proposals
    gov_proposals.set_proposal_status(pid2, 'passed')

    # blocks pagination
    bpage = client.get("/explorer/blocks?limit=2&offset=1").json()
    assert bpage["limit"] == 2
    assert bpage["offset"] == 1
    assert bpage["total"] == 5
    assert len(bpage["items"]) == 2

    # transactions pagination
    tpage = client.get("/explorer/transactions?limit=4&offset=2").json()
    assert tpage["limit"] == 4
    assert tpage["offset"] == 2
    # total transactions = 5*3 =15
    assert tpage["total"] == 15

    # transaction sender filter (alice)
    talice = client.get("/explorer/transactions?sender=alice").json()
    assert all(tx["from"] == "alice" for tx in talice["items"])

    # transaction recipient filter (dave)
    tdave = client.get("/explorer/transactions?recipient=dave").json()
    assert all(tx["to"] == "dave" for tx in tdave["items"])

    # audit event_type filter
    a_evA = client.get("/explorer/audit?event_type=evA").json()
    assert all(a["event_type"] == "evA" for a in a_evA["items"])

    # audit actor_id filter
    a_actor = client.get(f"/explorer/audit?actor_id={u2['id']}").json()
    assert all(a["actor_id"] == u2["id"] for a in a_actor["items"])

    # validators active filter
    v_active = client.get("/explorer/validators?active=true").json()
    assert v_active["total"] >= 2

    # validators role filter
    v_role = client.get("/explorer/validators?role=admin").json()
    assert all(v["role"] == "admin" for v in v_role["items"])

    # governance status filter
    gov_passed = client.get("/explorer/governance?status=passed").json()
    assert all(item["proposal"]["status"] == "passed" for item in gov_passed["items"])