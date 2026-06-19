class Transaction:

    def __init__(
        self,
        sender,
        receiver,
        amount,
        tx_type="transfer"
    ):

        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.tx_type = tx_type

    def to_dict(self):

        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "tx_type": self.tx_type
        }
