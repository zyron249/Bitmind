from datetime import datetime, timedelta
from typing import List, Optional
import uuid

from .node import Node
from .peer import Peer


class DiscoveryService:
    """Simple in-memory discovery service for registering and discovering peers."""

    def __init__(self):
        # no persistent storage, in-memory only
        pass

    def _make_peer_id(self, host: str, port: int) -> str:
        """Generate a deterministic peer id for a given host:port using uuid5."""
        try:
            name = f"{host}:{port}"
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, name))
        except Exception:
            return str(uuid.uuid4())

    def register_peer(
        self, node: Node, host: str, port: int, seen_at: Optional[datetime] = None
    ) -> Peer:
        """Register a peer on the given node and return the Peer object."""
        seen_at = seen_at or datetime.utcnow()
        pid = self._make_peer_id(host, port)
        peer = Peer(peer_id=pid, host=host, port=port, last_seen=seen_at)
        node.add_peer(peer)
        return peer

    def discover_peers(self, node: Node, max_peers: Optional[int] = None) -> List[Peer]:
        """Return known peers for the node, optionally limited by max_peers."""
        peers = node.list_peers()
        if max_peers is not None:
            return peers[:max_peers]
        return peers

    def remove_stale_peers(self, node: Node, stale_after_seconds: int) -> List[str]:
        """Remove peers not seen within stale_after_seconds and return their ids."""
        cutoff = datetime.utcnow() - timedelta(seconds=stale_after_seconds)
        removed: List[str] = []
        for p in list(node.list_peers()):
            if p.last_seen < cutoff:
                node.remove_peer(p.peer_id)
                removed.append(p.peer_id)
        return removed
