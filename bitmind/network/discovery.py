from datetime import datetime, timedelta
from typing import List, Optional
import uuid

from .node import Node
from .peer import Peer


class DiscoveryService:
    def __init__(self):
        # no persistent storage, in-memory only
        pass

    def _make_peer_id(self, host: str, port: int) -> str:
        # deterministic-ish: use uuid5 namespace DNS to produce the same id for same host:port
        # fallback to uuid4 if uuid5 unexpectedly fails
        try:
            name = f"{host}:{port}"
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, name))
        except Exception:
            return str(uuid.uuid4())

    def register_peer(self, node: Node, host: str, port: int, seen_at: Optional[datetime] = None) -> Peer:
        seen_at = seen_at or datetime.utcnow()
        pid = self._make_peer_id(host, port)
        peer = Peer(peer_id=pid, host=host, port=port, last_seen=seen_at)
        node.add_peer(peer)
        return peer

    def discover_peers(self, node: Node, max_peers: Optional[int] = None) -> List[Peer]:
        peers = node.list_peers()
        if max_peers is not None:
            return peers[:max_peers]
        return peers

    def remove_stale_peers(self, node: Node, stale_after_seconds: int) -> List[str]:
        cutoff = datetime.utcnow() - timedelta(seconds=stale_after_seconds)
        removed = []
        for p in list(node.list_peers()):
            if p.last_seen < cutoff:
                node.remove_peer(p.peer_id)
                removed.append(p.peer_id)
        return removed
