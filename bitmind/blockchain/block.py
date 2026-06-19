import hashlib
import json
import time
from typing import List
from .transaction import Transaction

class Block:
    def __init__(self, index: int, transactions: List[Transaction], prev_hash: str, timestamp: float | None = None, nonce: int = 0):
        self.index = index
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.transactions = transactions  # list of Transaction objects
        self.prev_hash = prev_hash
        self.nonce = nonce
        self.merkle_root = self.calculate_merkle_root()
        self.hash = self.calculate_hash()

    def calculate_merkle_root(self) -> str:
        txids = [tx.txid for tx in self.transactions]
        # compute merkle root using pairwise sha256
        if len(txids) == 0:
            return hashlib.sha256(b"").hexdigest()
        current = txids[:]
        while len(current) > 1:
            next_level = []
            for i in range(0, len(current), 2):
                left = current[i]
                right = current[i + 1] if i + 1 < len(current) else current[i]
                combined = (left + right).encode()
                h = hashlib.sha256(combined).hexdigest()
                next_level.append(h)
            current = next_level
        return current[0]

    def calculate_hash(self) -> str:
        header = {
            "index": self.index,
            "timestamp": self.timestamp,
            "prev_hash": self.prev_hash,
            "merkle_root": self.merkle_root,
            "nonce": self.nonce,
        }
        header_bytes = json.dumps(header, sort_keys=True).encode()
        return hashlib.sha256(header_bytes).hexdigest()

    def to_dict(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [t.to_dict() for t in self.transactions],
            "prev_hash": self.prev_hash,
            "nonce": self.nonce,
            "merkle_root": self.merkle_root,
            "hash": self.hash,
        }
