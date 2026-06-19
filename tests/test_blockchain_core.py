from bitmind.blockchain.wallet import Wallet
from bitmind.blockchain.transaction import Transaction
from bitmind.blockchain.merkle import merkle_root_from_txids
from bitmind.blockchain.genesis import create_genesis_block
from bitmind.blockchain.chain import Chain
from bitmind.blockchain.block import Block


def test_wallet_and_address():
    w = Wallet.create_wallet()
    assert "private_key" in w and "address" in w
    assert len(w["private_key"]) == 64
    assert len(w["address"]) == 64


def test_transaction_and_txid():
    tx = Transaction(sender="a", recipient="b", amount=1.23)
    assert tx.txid is not None
    # recomputing should match
    assert tx.calculate_txid() == tx.txid


def test_merkle_root_even_odd():
    txs = [Transaction("a", "b", i) for i in range(4)]
    txids = [t.txid for t in txs]
    r = merkle_root_from_txids(txids)
    assert isinstance(r, str) and len(r) == 64
    # odd number
    txs2 = [Transaction("a", "b", i) for i in range(3)]
    txids2 = [t.txid for t in txs2]
    r2 = merkle_root_from_txids(txids2)
    assert isinstance(r2, str) and len(r2) == 64


def test_genesis_and_chain_add_validate():
    genesis = create_genesis_block()
    chain = Chain(genesis)
    # create transactions and block
    txs = [Transaction("addr1", "addr2", 10), Transaction("addr2", "addr3", 5)]
    block = chain.create_block(txs)
    added = chain.add_block(block)
    assert added is True
    assert chain.validate_chain() is True

    # tamper with a transaction in block (without updating merkle/hash)
    chain.blocks[1].transactions[0].amount = 9999
    # validation should fail
    assert chain.validate_chain() is False


def test_block_hash_changes_with_nonce_and_content():
    genesis = create_genesis_block()
    chain = Chain(genesis)
    txs = [Transaction("x", "y", 1)]
    block = chain.create_block(txs)
    h1 = block.hash
    # change nonce and recalc
    block.nonce = 1
    block.merkle_root = block.calculate_merkle_root()
    block.hash = block.calculate_hash()
    h2 = block.hash
    assert h1 != h2
