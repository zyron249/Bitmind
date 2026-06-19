from blockchain.block import Block

class Blockchain:

    def __init__(self):

        self.chain = []
        self.pending = []

        self.create_genesis()

    def create_genesis(self):

        genesis = Block(
            0,
            [],
            "0"
        )

        self.chain.append(
            genesis
        )

    def latest(self):

        return self.chain[-1]

    def add_transaction(
        self,
        tx
    ):

        self.pending.append(
            tx
        )

    def create_block(self):

        block = Block(
            len(self.chain),
            self.pending,
            self.latest().hash
        )

        self.pending = []

        self.chain.append(
            block
        )

        return block
