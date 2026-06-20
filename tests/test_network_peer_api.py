from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from bitmind.api.network import app, get_node, get_discovery


@pytest.fixture(autouse=True)
def reset_node():
    node = get_node()
    node.peers.clear()
    node.blockchain_height = 0
    yield
    node.peers.clear()
    node.blockchain_height = 0


def test_register_and_list_peers_api():
    client = TestClient(app)

    # register a peer
    r = client.post("/network/peers", json={"host": "127.0.0.1", "port": 8000})
    assert r.status_code == 200
    data = r.json()
    assert "peer_id" in data
    pid = data["peer_id"]

    # list peers
    r2 = client.get("/network/peers")
    assert r2.status_code == 200
    pl = r2.json()["peers"]
    assert any(p["peer_id"] == pid for p in pl)


def test_delete_peer_api():
    client = TestClient(app)
    # create via discovery to have deterministic id
    r = client.post("/network/peers", json={"host": "10.0.0.1", "port": 9000})
    pid = r.json()["peer_id"]

    # delete
    rd = client.delete(f"/network/peers/{pid}")
    assert rd.status_code == 200
    assert rd.json() == {"removed": True}

    # deleting again returns 404
    rd2 = client.delete(f"/network/peers/{pid}")
    assert rd2.status_code == 404


def test_heartbeat_updates_last_seen_and_missing():
    client = TestClient(app)

    r = client.post("/network/peers", json={"host": "192.168.0.1", "port": 7000})
    assert r.status_code == 200
    data = r.json()
    pid = data["peer_id"]
    old_last_seen = datetime.fromisoformat(data["last_seen"]) 

    # heartbeat
    hb = client.post(f"/network/peers/{pid}/heartbeat")
    assert hb.status_code == 200
    new = hb.json()
    new_last_seen = datetime.fromisoformat(new["last_seen"]) 
    assert new_last_seen >= old_last_seen

    # missing peer heartbeat
    resp = client.post("/network/peers/not-a-peer/heartbeat")
    assert resp.status_code == 404

    # missing peer delete
    rdel = client.delete("/network/peers/not-a-peer")
    assert rdel.status_code == 404