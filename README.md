# Bitmind P2P Network

This project includes an in-memory, deterministic P2P node network implementation for testing and local development.

## Peer registration API

Register a peer (example):

curl -X POST "http://localhost:8000/network/peers" -H "Content-Type: application/json" -d '{"host":"127.0.0.1","port":8000}'

Response:
{
  "peer_id": "...",
  "host": "127.0.0.1",
  "port": 8000,
  "last_seen": "2026-06-20T00:00:00.000000"
}

List peers:

curl "http://localhost:8000/network/peers"

Delete a peer:

curl -X DELETE "http://localhost:8000/network/peers/<peer_id>"

Heartbeat (update last_seen):

curl -X POST "http://localhost:8000/network/peers/<peer_id>/heartbeat"

Notes:
- In-memory only (no real sockets or persistent storage).
- Deterministic peer IDs are generated from host:port using uuid5.
- No authentication in this v1.
