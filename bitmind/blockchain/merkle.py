import hashlib

def merkle_root_from_txids(txids: list[str]) -> str:
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
