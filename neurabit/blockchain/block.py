from hashlib import sha256
import json
import time

class Block:

    def __init__(
        self,
        index,
        transactions,
        previous_hash
    ):

        self.index = index
        self.timestamp = time.time()
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = 0

        self.hash = self.calculate_hash()

    def calculate_hash(self):

        data = json.dumps(
            {
                "index": self.index,
                "timestamp": self.timestamp,
                "transactions": self.transactions,
                "previous_hash": self.previous_hash,
                "nonce": self.nonce
            },
            sort_keys=True
        )

        return sha256(
            data.encode()
        ).hexdigest()
