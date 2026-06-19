from ecdsa import SigningKey
from ecdsa import SECP256k1

class Wallet:

    def __init__(self):

        self.private_key = SigningKey.generate(
            curve=SECP256k1
        )

        self.public_key = (
            self.private_key
            .verifying_key
        )

    def address(self):

        return (
            self.public_key
            .to_string()
            .hex()
        )
