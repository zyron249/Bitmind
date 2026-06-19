import hashlib
import secrets

class Wallet:
    @staticmethod
    def create_wallet():
        # generate a random private key (hex) and derive a simple address
        private_key = secrets.token_hex(32)
        # derive address as sha256 of private key
        address = hashlib.sha256(private_key.encode()).hexdigest()
        return {"private_key": private_key, "address": address}
