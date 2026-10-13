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
private key is needed to browse it. A MetaMask wallet with testnet MON is needed to create or
settle rentals. The Docker nodes are local stand-ins for provider health endpoints; Docker
does not run the contract or create blockchain rentals.

From the repository root:

```bash
make install       # create .venv and install Python dependencies
make ui-install    # install frontend dependencies
make ui            # start the frontend at http://localhost:5173
```

### Run the Docker A/B uptime demo

The oracle only reports rentals whose provider **and** renter addresses are configured. Before
starting it, prepare the root `.env` and `oracle/config.toml`:

```bash
cp .env.example .env
make config
```

Edit `.env` and set `MONAD_RPC` and `REPORTER_KEYS`. `REPORTER_KEYS` must contain the team's
testnet reporter keys that are authorized by the deployed contract; each reporter wallet needs
testnet MON for gas. These are backend secrets: keep `.env` local and never put these keys in the
frontend or commit them.

Edit `oracle/config.toml`. Replace the example addresses with the actual addresses you will use:

```toml
[nodes]
"<provider-A-address>" = "http://127.0.0.1:8081"
"<provider-B-address>" = "http://127.0.0.1:8082"

[renters]
allow = ["<renter-wallet-address>"]
```

Use valid `0x` addresses, without the angle brackets. The provider addresses must match those
entered on the Create Rental form, and the renter address must match the connected wallet. An
empty or mismatched allow-list means the oracle ignores the rental and sends no reports.

Run these commands in separate terminals from the repository root:

```bash
make nodes-up      # terminal 1: start node-a and node-b in Docker
make oracle        # terminal 2: start the reporter service; leave it running
make ui            # terminal 3: start the frontend
```

The demo nodes answer `http://127.0.0.1:8081/health` (A) and `http://127.0.0.1:8082/health`
(B). Create one four-slot rental for each provider with a 30-second interval and 75% threshold.
Wait until the oracle log says `track rental=...` for both rentals and B's rental has started.
Then, from a fourth terminal, stop **only** node B:

```bash
make stop-b
```

Keep B stopped for at least two full slots, then restore it with `make start-b`. The oracle log
should show failed probes and `up=False` reports for B, while A remains up. With two down slots
out of four, B's rental misses the 75% threshold and refunds the renter after settlement. Do not
run `make nodes-down` during this demo; it removes both Docker nodes. Use `make nodes-ps` to
check their status.

After the rental ends, allow the 30-second reporting grace period before pressing **Settle**.
The **Finalize** button appears after the 60-second challenge window. Finalize credits the payee;
the payee must connect their own wallet and use **Withdraw** to transfer that credit. Testnet MON
has no real value.

The automated test suites do not need a wallet, Docker, or private keys:

```bash
make test
make ui-test
cd indexer && pnpm install && pnpm test
```

### Optional: run the Envio indexer locally

Start the indexer in another terminal:

```bash
cd indexer
pnpm install
pnpm envio dev
```

The local GraphQL endpoint is `http://localhost:8080/v1/graphql`. To make the UI use it,
copy `frontend/.env.example` to `frontend/.env.local` and set
`VITE_INDEXER_URL=http://localhost:8080/v1/graphql`; restart the UI after changing the file.
If this variable is unset, the rentals list and history use direct Monad RPC instead.
See `make help` for all available targets, including `make ui-build` and `make nodes-down`.

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
