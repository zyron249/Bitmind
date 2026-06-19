from .block import Block
from .transaction import Transaction


def create_genesis_block() -> Block:
    # genesis has index 0, no transactions, prev_hash of 64 zeros
    genesis = Block(index=0, transactions=[], prev_hash="0" * 64)
    return genesis
