from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any
from datetime import datetime

from bitmind.network.node import Node
from bitmind.network.discovery import DiscoveryService

app = FastAPI()

# In-memory singleton node and discovery service for the application
_node = Node()
_discovery = DiscoveryService()

class RegisterPeerRequest(BaseModel):
    host: str = Field(..., example="127.0.0.1")
    port: int = Field(..., example=8000)

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

@app.post("/network/peers")
def register_peer(req: RegisterPeerRequest) -> Dict[str, Any]:
    peer = _discovery.register_peer(_node, req.host, req.port)
    return peer.to_dict()

@app.delete("/network/peers/{peer_id}")
def delete_peer(peer_id: str) -> Dict[str, Any]:
    removed = _node.remove_peer(peer_id)
    if not removed:
        raise HTTPException(status_code=404, detail="peer not found")
    return {"removed": True}

@app.post("/network/peers/{peer_id}/heartbeat")
def peer_heartbeat(peer_id: str) -> Dict[str, Any]:
    updated = _node.update_peer_last_seen(peer_id, seen_at=datetime.utcnow())
    if not updated:
        raise HTTPException(status_code=404, detail="peer not found")
    peer = _node.get_peer(peer_id)
    return peer.to_dict()

# Small helpers to manipulate the in-memory node from tests or other modules
def get_node() -> Node:
    return _node

def get_discovery() -> DiscoveryService:
    return _discovery
