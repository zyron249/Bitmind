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


def test_explorer_endpoints(client):
    # create some data
    u = client.post("/users", json={"username": "alice"}).json()
    # add audit event
    client.post("/validators", json={"user_id": u["id"], "role": "validator"})
    # create blocks and transactions in memory
    from bitmind.core import models as core_models
    block0 = {"index": 0, "hash": "abc", "transactions": [{"txid": "tx1", "from": "a", "to": "b", "amount": 10}]} 
    block1 = {"index": 1, "hash": "def", "transactions": [{"txid": "tx2", "from": "c", "to": "d", "amount": 20}]} 
    core_models.InMemoryDB.blocks = [block0, block1]

    # governance proposals
    client.post("/governance/proposals", json={"title":"G1","description":"","created_by":u["id"]})

    # create audit event
    from bitmind.core import audit as core_audit
    core_audit.add_audit_event(event_type="test", actor_id=u["id"], target_id=None, reason="test")

    # create a PoI submission
    task = client.post("/tasks", json={"prompt":"1+1","answer_key":"2","is_test":True}).json()
    client.post("/poi/evaluate", json={"user_id": u["id"], "task_id": task["id"], "submission_content": "2"})

    # summary
    s = client.get("/explorer/summary").json()
    assert s["total_blocks"] == 2
    assert s["total_transactions"] == 2
    assert s["total_validators"] >= 1

    # blocks
    blocks = client.get("/explorer/blocks").json()
    assert isinstance(blocks, dict)
    assert isinstance(blocks["items"], list)
    b0 = client.get("/explorer/blocks/0").json()
    assert b0["hash"] == "abc"
    # missing block
    r = client.get("/explorer/blocks/10")
    assert r.status_code == 404

    # transactions
    txs = client.get("/explorer/transactions").json()
    assert isinstance(txs, dict)
    assert isinstance(txs["items"], list)
    tx1 = client.get("/explorer/transactions/tx1").json()
    assert tx1["txid"] == "tx1"
    r2 = client.get("/explorer/transactions/notx")
    assert r2.status_code == 404

    # validators
    vals = client.get("/explorer/validators").json()
    assert isinstance(vals, dict)
    assert isinstance(vals["items"], list)

    # governance
    gov = client.get("/explorer/governance").json()
    assert isinstance(gov, dict)
    assert isinstance(gov["items"], list)

    # audit
    audits = client.get("/explorer/audit").json()
    assert isinstance(audits, dict)
    assert isinstance(audits["items"], list)
