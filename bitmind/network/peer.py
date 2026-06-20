from dataclasses import dataclass
from datetime import datetime
from typing import Dict


@dataclass
class Peer:
    peer_id: str
    host: str
    port: int
    last_seen: datetime

    def to_dict(self) -> Dict[str, str]:
        """Serialize Peer to a dictionary suitable for JSON responses."""
        return {
            "peer_id": self.peer_id,
            "host": self.host,
            "port": self.port,
            "last_seen": self.last_seen.isoformat(),
        }
