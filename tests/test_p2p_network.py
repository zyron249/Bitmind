import time
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from bitmind.network.node import Node
from bitmind.network.discovery import DiscoveryService
from bitmind.api.network import app, get_node, get_discovery


@pytest.fixture(autouse=True)
def reset_node():
    # Reset global node between tests to ensure determinism
    node = get_node()
    node.peers.clear()
    node.blockchain_height = 0
    yield
    node.peers.clear()
    node.blockchain_height = 0


def test_add_and_remove_peer():
    node = get_node()
    discovery = get_discovery()

    peer = discovery.register_peer(node, "127.0.0.1", 8000)
    assert peer.peer_id in node.peers
    assert len(node.list_peers()) == 1

    removed = node.remove_peer(peer.peer_id)
    assert removed is True
    assert len(node.list_peers()) == 0


def test_discover_peers():
    node = get_node()
    discovery = get_discovery()

    p1 = discovery.register_peer(node, "127.0.0.1", 8000)
    p2 = discovery.register_peer(node, "127.0.0.2", 8001)
    found = discovery.discover_peers(node)
    ids = {p.peer_id for p in found}
    assert ids == {p1.peer_id, p2.peer_id}

    limited = discovery.discover_peers(node, max_peers=1)
    assert len(limited) == 1


def test_remove_stale_peers():
    node = get_node()
    discovery = get_discovery()

    now = datetime.utcnow()
    old_time = now - timedelta(seconds=3600)

    p_old = discovery.register_peer(node, "10.0.0.1", 9000, seen_at=old_time)
    p_new = discovery.register_peer(node, "10.0.0.2", 9001, seen_at=now)

    removed = discovery.remove_stale_peers(node, stale_after_seconds=60)
    assert p_old.peer_id in removed
    assert p_new.peer_id not in removed
    assert len(node.list_peers()) == 1


def test_network_status_and_peers_endpoint():
    client = TestClient(app)
    node = get_node()
    discovery = get_discovery()

    discovery.register_peer(node, "1.2.3.4", 7000)
    discovery.register_peer(node, "5.6.7.8", 7001)
    node.blockchain_height = 42

    r = client.get("/network/status")
    assert r.status_code == 200
    data = r.json()
    assert "node_id" in data
    assert data["peer_count"] == 2
    assert data["blockchain_height"] == 42

    r2 = client.get("/network/peers")
    assert r2.status_code == 200
    pldata = r2.json()
    assert "peers" in pldata
    assert len(pldata["peers"]) == 2
    for p in pldata["peers"]:
        assert "peer_id" in p and "host" in p and "port" in p and "last_seen" in p
