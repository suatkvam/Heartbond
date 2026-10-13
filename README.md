# Heartbond — pay per heartbeat

Monad Metropolis hackathon project (working title was "GPU SLA Escrow"; the contract is still
named `GpuSlaEscrow`).

On-chain escrow that pays a GPU provider or refunds a renter based on per-slot uptime
reports. Anyone can trigger settlement; finality is a fixed timeout. Uptime data comes
from team-held reporter keys (not trustless — see docs/PRD.md §10, §13).

| Doc | For |
|---|---|
| `docs/SPEC.md` | exact rules with IDs (build + tests) |
| `docs/PRD.md` | research, claims, risks |
| `docs/UI_HANDOFF.md` | frontend teammate (TR) |
| `docs/PLAN.md` | work order + day-0 checklist (TR) |
| `CLAUDE.md`, `.claude/agents/` | Claude Code setup |

```bash
pip install -r requirements.txt
pytest -q tests/                      # views pass, the rest go green as you implement
python scripts/smoke_test.py          # day-0 check on Monad Testnet (needs .env)
```
_The pitch-factchecker agent replaces this README before submission._

## How Heartbond uses Envio

The Envio HyperIndex in `indexer/` indexes all six `GpuSlaEscrow` events from the Monad
Testnet deployment. It derives rental state, slot reports and transaction history, objections,
withdrawals, provider uptime totals, and reporter report counts. It reads Monad Testnet RPC in
bounded 100-block ranges, so no Envio token is needed for local sync. Run
`cd indexer && pnpm install && pnpm envio dev`; the local GraphQL endpoint is served at
`http://localhost:8080/v1/graphql`.

When `VITE_INDEXER_URL` points to that GraphQL endpoint, the frontend uses Envio for the rentals
list, rental activity history, and cross-rental provider statistics. The rental detail's live
contract state, slot reads, wallet credits and every transaction continue to use Monad RPC. If
`VITE_INDEXER_URL` is unset, the rentals list and history scan fall back to direct RPC; the
provider statistics panel scans rental state through RPC. No contract, oracle or ABI feature
depends on Envio, and no wallet write is sent through the indexer.
