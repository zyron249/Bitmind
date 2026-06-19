from .block import Block
from .chain import Chain


def validate_block(block: Block) -> bool:
    # check merkle and hash
    if block.merkle_root != block.calculate_merkle_root():
        return False
    if block.hash != block.calculate_hash():
        return False
    return True


def validate_chain(chain: Chain) -> bool:
    return chain.validate_chain()
