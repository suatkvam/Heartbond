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
make install
make test
```

## Run locally

You need Python 3.12+, Node.js 20+, npm, pnpm, Docker with Compose, and GNU Make. The UI can
run against the already deployed Monad Testnet contract; no local contract deployment or
private key is needed to browse it.

From the repository root:

```bash
make install       # create .venv and install Python dependencies
make ui-install    # install frontend dependencies
make config        # create oracle/config.toml from the example (optional)
make nodes-up      # start the two demo GPU nodes in Docker (optional)
make ui            # start the frontend at http://localhost:5173
```

To run the local Envio indexer as well, open another terminal:

```bash
cd indexer
pnpm install
pnpm envio dev
```

The local GraphQL endpoint is `http://localhost:8080/v1/graphql`. To make the UI use it,
copy `frontend/.env.example` to `frontend/.env.local` and set
`VITE_INDEXER_URL=http://localhost:8080/v1/graphql`; restart the UI after changing the file.
If this variable is unset, the rentals list and history use direct Monad RPC instead.

For the oracle demo, fill `oracle/config.toml` with the provider and renter wallet addresses
you will use, and create a root `.env` with the Monad RPC URL and reporter private keys. Keep
that `.env` local and never put private keys in `frontend/.env.local`. Then run `make oracle`
in another terminal. See `make help` for the other available targets, including `make ui-test`,
`make ui-build`, and `make nodes-down`.

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
