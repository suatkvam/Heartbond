# Oracle service

One Python process (SPEC §4, H-1..H-9) that:

1. discovers rentals from `RentalCreated` logs, polled in chunks from the deploy block, and
   serves only those that pass both gates below;
2. probes `GET <node_url>/health` of each rental's provider every 5 s while the rental runs;
3. after each slot completes, sends `report_uptime(rental_id, slot, up)` from the key
   `REPORTER_KEYS[rental_id % len(keys)]`, with an explicit gas limit (estimate × 1.2),
   retrying until `end + REPORT_GRACE` or until the rental's report budget is spent;
4. serves a small control API on `127.0.0.1:8787` (force-down backup, status for the UI panel).

A slot is **Up** only if at least one probe ran in it and every probe returned HTTP 200
within 2 s. A slot with a failed probe, or with no probe at all, is **Down**.

## Which rentals are served (H-8)

Creating a rental on-chain is open to anyone. The service is narrower by choice. It serves
a rental only if **both** hold, decided from the `RentalCreated` event alone, before any
probe, `get_slots` call or transaction:

1. **provider gate** — the provider address has a node under `[nodes]` in `oracle/config.toml`;
2. **renter gate** — the renter address is in `[renters] allow` in the same file.

Anything else is ignored with one log line (`reason=no-node-in-config` or
`reason=renter-not-allowed`): not probed, not reported, not in the control API (`/rentals`
omits it, `/rentals/{id}` is 404). Its slots stay empty on-chain, `settle` counts them as
Down, and the escrow is **refunded to its renter**. So a rental created from any other
wallet — a judge's, for example — gets no reports and ends as a refund, even when it names
a healthy demo provider. To have such a rental reported, add the wallet to `[renters] allow`
and restart the service before the rental starts.

A missing or empty `[renters] allow` means **no rental is served**; the service prints
`WARNING renter allow-list is empty` at start.

## Report budget (H-9)

Per rental the service broadcasts at most `2 × N` `report_uptime` transactions (`N` = slot
count):

- the **first** broadcast of each slot is always allowed (at most `N` of these);
- every later broadcast of a slot — a re-send after a failed or reverted transaction, or a
  same-nonce fee replacement of a stuck one — comes out of one pool of `N` re-submissions
  shared by the whole rental.

A send that never reached the node does not count: one refused by the gas or fee cap, one
whose gas estimate reverts (e.g. the slot is already on-chain), or one where the RPC call
itself failed. When the pool is empty the service logs `budget-spent rental=… used=…/…`
once, stops retrying the slots that need a re-submission, and still sends the first report
of slots that complete later. Slots left unreported count as Down at `settle`, so a rental
that uses up its budget can end as a refund even though the node was up.

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
# edit oracle/config.toml:
#   [nodes]    the two demo provider addresses in place of the placeholders
#   [renters]  allow = ["0x<demo renter wallet>"]  - every wallet that will create a demo rental
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

At start the service prints the contract, the number of nodes and allow-listed renters, the
reporter addresses, a `WARNING` line for every reporter key below 10 MON, and a `WARNING`
line if the renter allow-list is empty. It then logs one line per probe and per transaction:

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
reported by two keys, an objection that changes nothing, and a rental from a wallet that is
not on the allow-list (no reports, refund) — each through `settle`, `finalize` (third
account) and `withdraw` (payee). `oracle/tests/test_h8_h9.py` covers the two gates and the
report budget.

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
- A rental is ignored unless its provider is under `[nodes]` **and** its renter is in
  `[renters] allow`: no probes, no reports (its slots stay empty, which `settle` counts as
  Down, so it refunds its renter). The config is read once at start; restart after editing it.
- **The report budget is in memory. A restart resets it**: after a restart every rental's
  cap starts again from zero, so across restarts a rental can get more than `2 × N`
  transactions. Another reason not to restart during a rental.
- Reporter keys are shared between rentals (`rental_id % len(keys)`). If a transaction stays
  stuck after the budget stopped its fee replacements, later transactions from the same key
  queue behind its nonce — for that rental and for other rentals on that key.
- Reporting stops at `end + REPORT_GRACE` (30 s). A slot not reported by then stays empty.
- If the RPC refuses the `eth_getLogs` range, lower `LOG_CHUNK`.
