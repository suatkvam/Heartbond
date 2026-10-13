# Demo GPU nodes

Two stand-ins for a provider's GPU node (SPEC H-2, D-04). Each answers `GET /health`
with `200 {"ok": true, "node": "<name>"}`; any other path is 404. Stdlib Python only.

| Container | URL |
|---|---|
| `node-a` | `http://127.0.0.1:8081/health` |
| `node-b` | `http://127.0.0.1:8082/health` |

Run from the repo root:

```sh
docker compose -f docker/docker-compose.yml up -d --build   # start both nodes
curl -s http://127.0.0.1:8081/health; curl -s http://127.0.0.1:8082/health   # check
docker stop node-b      # node-b probes fail immediately (connection refused); node-a unaffected
docker start node-b     # node-b healthy again
docker compose -f docker/docker-compose.yml down             # remove both
```

Map each provider address to a different node in the oracle config: the compliant and
non-compliant demo runs overlap, so stopping `node-b` must not fail the other rental.
For a non-compliant result keep the node stopped for at least two slots (SPEC §5).
