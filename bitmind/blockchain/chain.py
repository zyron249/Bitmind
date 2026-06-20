from .block import Block
from .transaction import Transaction
from typing import List

class Chain:
    def __init__(self, genesis_block: Block):
        self.blocks: List[Block] = [genesis_block]

    def get_last_block(self) -> Block:
        return self.blocks[-1]

    def create_block(self, transactions: List[Transaction]) -> Block:
        last = self.get_last_block()
        index = last.index + 1
        prev_hash = last.hash
        block = Block(index=index, transactions=transactions, prev_hash=prev_hash)
        return block

    def add_block(self, block: Block) -> bool:
        # basic validation: prev_hash must match last block
        last = self.get_last_block()
        if block.prev_hash != last.hash:
            return False
        # each transaction payload must match its txid
        if any(tx.txid != tx.calculate_txid() for tx in block.transactions):
            return False
        # recompute merkle and hash and ensure they match
        if block.merkle_root != block.calculate_merkle_root():
            return False
        if block.hash != block.calculate_hash():
            return False
        self.blocks.append(block)
        return True

    def validate_chain(self) -> bool:
        # Validate entire chain integrity
        for i in range(1, len(self.blocks)):
            current = self.blocks[i]
            prev = self.blocks[i - 1]
            # Check prev_hash link
            if current.prev_hash != prev.hash:
                return False
            # Verify merkle root
            if current.merkle_root != current.calculate_merkle_root():
                return False
            # Verify transactions were not tampered with
            if any(tx.txid != tx.calculate_txid() for tx in current.transactions):
                return False
            # Verify block hash
            if current.hash != current.calculate_hash():
                return False
        return True
