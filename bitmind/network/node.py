from typing import Dict, List, Optional
from uuid import uuid4
from datetime import datetime
from .peer import Peer


class Node:
    """In-memory representation of a node in the P2P network."""

    def __init__(self, node_id: Optional[str] = None):
        self.node_id = node_id or str(uuid4())
        # peers stored by peer_id
        self.peers: Dict[str, Peer] = {}
        self.blockchain_height: int = 0

    def add_peer(self, peer: Peer) -> None:
        """Add or update a peer."""
        self.peers[peer.peer_id] = peer

    def remove_peer(self, peer_id: str) -> bool:
        """Remove peer by id. Returns True if removed."""
        return self.peers.pop(peer_id, None) is not None

    def list_peers(self) -> List[Peer]:
        """Return a list of peers currently known to the node."""
        return list(self.peers.values())

    def update_peer_last_seen(
        self, peer_id: str, seen_at: Optional[datetime] = None
    ) -> bool:
        """Update the last_seen timestamp for a peer. Returns True if peer exists."""
        seen_at = seen_at or datetime.utcnow()
        peer = self.peers.get(peer_id)
        if not peer:
            return False
        peer.last_seen = seen_at
        self.peers[peer_id] = peer
        return True

    def get_peer(self, peer_id: str) -> Optional[Peer]:
        """Retrieve a peer by id, or None if not found."""
        return self.peers.get(peer_id)
