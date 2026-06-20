from fastapi import FastAPI
from typing import Dict, Any

from bitmind.network.node import Node
from bitmind.network.discovery import DiscoveryService

app = FastAPI()

# In-memory singleton node and discovery service for the application
_node = Node()
_discovery = DiscoveryService()

@app.get("/network/status")
def network_status() -> Dict[str, Any]:
    return {
        "node_id": _node.node_id,
        "peer_count": len(_node.peers),
        "blockchain_height": _node.blockchain_height,
    }

@app.get("/network/peers")
def network_peers() -> Dict[str, Any]:
    peers = [_p.to_dict() for _p in _node.list_peers()]
    return {"peers": peers}

# Small helpers to manipulate the in-memory node from tests or other modules
def get_node() -> Node:
    return _node

def get_discovery() -> DiscoveryService:
    return _discovery
