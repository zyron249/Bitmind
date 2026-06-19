import hashlib
import json
import time
from dataclasses import dataclass, asdict

@dataclass
class Transaction:
    sender: str
    recipient: str
    amount: float
    timestamp: float | None = None
    txid: str | None = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.txid is None:
            self.txid = self.calculate_txid()

    def to_dict(self):
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "timestamp": self.timestamp,
            "txid": self.txid,
        }

    def calculate_txid(self) -> str:
        payload = {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "timestamp": self.timestamp,
        }
        b = json.dumps(payload, sort_keys=True).encode()
        return hashlib.sha256(b).hexdigest()
