# Oracle service

One Python process (SPEC §4, H-1..H-7) that:

1. discovers rentals from `RentalCreated` logs, polled in chunks from the deploy block;
2. probes `GET <node_url>/health` of each rental's provider every 5 s while the rental runs;
3. after each slot completes, sends `report_uptime(rental_id, slot, up)` from the key
   `REPORTER_KEYS[rental_id % len(keys)]`, with an explicit gas limit (estimate × 1.2),
   retrying until `end + REPORT_GRACE`;
4. serves a small control API on `127.0.0.1:8787` (force-down backup, status for the UI panel).

A slot is **Up** only if at least one probe ran in it and every probe returned HTTP 200
within 2 s. A slot with a failed probe, or with no probe at all, is **Down**.

## Honest limits

- The reporter keys are held by the team. That is **one trust root**: whoever holds the
  keys decides what the contract sees. Settlement is permissionless (anyone can trigger
  it); the uptime data is not trustless.
- The health probe proves the endpoint was **reachable**, not that a GPU did any work.
  The demo node is a container, not a GPU.
- The control API has no authentication. It binds to `127.0.0.1` only; do not expose it.

## Status: the contract is not deployed yet

`shared/deployments/monad-testnet.json` has `address: null`. Until a deploy fills it,
`python -m oracle` exits immediately with `oracle: contract is not deployed - ...` and
touches no network. Everything below the setup section works only after the deploy.

## Setup (team WSL machine)

From the repo root:

```sh
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp oracle/config.example.toml oracle/config.toml
# edit oracle/config.toml: put the two demo provider addresses in place of the placeholders
export MONAD_RPC=https://testnet-rpc.monad.xyz
export REPORTER_KEYS=0x...,0x...    # testnet keys only; never commit them
```

The process does not read `.env`; export the variables (or `set -a; source .env; set +a`).
`oracle/config.toml` holds only addresses and URLs — never put a key in it.

Optional variables: `ORACLE_CONFIG` (default `oracle/config.toml`), `LOG_CHUNK` (blocks
per `eth_getLogs`, default 1000), `ORACLE_API_PORT` (default 8787).

## Run

```sh
docker compose -f docker/docker-compose.yml up -d --build   # node-a :8081, node-b :8082
python -m oracle                                            # Ctrl-C to stop
```

At start the service prints the contract, the reporter addresses, and a `WARNING` line for
every reporter key below 10 MON. It then logs one line per probe and per transaction:

```text
probe provider=0x... url=http://127.0.0.1:8082 ok=True latency_ms=3 status=200
tx hash=0x... rental=2 slot=1 up=False reporter=0x...
confirmed hash=0x... rental=2 slot=1 up=False
```

## Demo actions

```sh
docker stop node-b      # node-b probes fail at once; keep it stopped for >= 2 slots (SPEC §5)
docker start node-b     # healthy again
```

Backup if Docker misbehaves on stage — force slots Down through the control API (it only
affects slots whose report has not been sent yet):

```sh
curl -s -X POST http://127.0.0.1:8787/rentals/2/force-down \
     -H 'content-type: application/json' -d '{"slots": [2, 3]}'
curl -s -X DELETE http://127.0.0.1:8787/rentals/2/force-down    # clear all marks on rental 2
curl -s http://127.0.0.1:8787/rentals/2                         # per-slot probe counts and tx hashes
```

## Control API

`http://127.0.0.1:8787` (change the port with `ORACLE_API_PORT`). CORS is open for
`localhost` / `127.0.0.1` origins. Contract: `docs/UI_HANDOFF.md` §7.

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/health` | — | `{ ok, chainId, contract, reporters: [{ address, balanceMon }] }` |
| GET | `/nodes` | — | `[{ provider, url, lastProbe: { ok, at, latencyMs } }]` |
| GET | `/rentals` | — | `[{ rentalId, provider, slots: [...] }]` |
| GET | `/rentals/{id}` | — | `{ rentalId, slots: [{ slot, probesOk, probesTotal, forcedDown, reported, up, txHash }] }` |
| POST | `/rentals/{id}/force-down` | `{ "slots": [2, 3] }` | `{ ok: true }` |
| DELETE | `/rentals/{id}/force-down` | — | `{ ok: true }` |

## Tests

```sh
pytest -q oracle/tests/
```

No network and no real key: the tests compile the contract, run it on an in-process
eth-tester chain, generate throwaway keys, and move chain time instead of waiting.
`oracle/tests/test_e2e.py` runs the whole demo (SPEC §5 parameters) end to end: healthy
node, node down for two slots, force-down, a slot with no probe, two overlapping rentals
reported by two keys, and an objection that changes nothing — each through `settle`,
`finalize` (third account) and `withdraw` (payee).

### Manual check against the real containers

Done once on 2026-10-13 on the WSL machine (not part of `pytest`): both containers up, the
service's own tick loop run against `http://127.0.0.1:8081` / `:8082` with two rentals on
the local eth-tester chain, `docker stop node-b` after the first slot.

```text
probe provider=0x1eff... url=http://127.0.0.1:8082 ok=True latency_ms=3 status=200
probe provider=0x6813... url=http://127.0.0.1:8081 ok=True latency_ms=3 status=200
--- docker stop node-b
probe provider=0x1eff... url=http://127.0.0.1:8082 ok=False latency_ms=2 error=ConnectError
probe provider=0x6813... url=http://127.0.0.1:8081 ok=True latency_ms=3 status=200
--- result
node-a rental=1 slot=0 probes=6/6 verdict=Up onchain=Up
node-a rental=1 slot=1 probes=6/6 verdict=Up onchain=Up
node-b rental=2 slot=0 probes=6/6 verdict=Up onchain=Up
node-b rental=2 slot=1 probes=0/6 verdict=Down onchain=Down
```

To repeat the reachability part by hand: `curl -s http://127.0.0.1:8082/health` answers
before `docker stop node-b` and fails with "connection refused" after it.

## Operational notes

- Keep **every reporter key above 10 MON**; Monad charges the gas limit, not gas used.
- Keep the WSL machine awake for the whole rental. While the service is not ticking, no
  probe runs, and a slot with no probe is reported Down.
- The service uses **chain time** (latest block timestamp) for probes and slot completion,
  not the local clock.
- Probe counts live in memory. After a restart, completed slots that were not yet reported
  have zero probes and are reported Down. Slots already on-chain are left alone.
- **Do not restart the service during a rental**: probe results are in memory, so a slot in
  progress at restart is judged only by the probes made after the restart.
- A rental whose provider is not in `oracle/config.toml` is ignored: no probes, no reports
  (its slots stay empty, which `settle` counts as Down).
- Reporting stops at `end + REPORT_GRACE` (30 s). A slot not reported by then stays empty.
- If the RPC refuses the `eth_getLogs` range, lower `LOG_CHUNK`.
