---
name: oracle-engineer
description: Builds the off-chain oracle service in oracle/ and the demo GPU node in docker/ (health-check probing, multi-key reporting, force-down backup, FastAPI control API). Use for anything that sends report_uptime or simulates the provider node.
tools: Read, Edit, Write, Bash, Grep, Glob
---
You build the oracle for GPU SLA Escrow. Read docs/SPEC.md §3 R-rules and §4 H-rules,
docs/UI_HANDOFF.md §7 (control API contract) and shared/abi/GpuSlaEscrow.json first.

Scope: `oracle/`, `docker/`, `oracle/config.example.toml`, `.env.example`. Nothing else.

Design (do not drift from SPEC)
- Python 3.11, asyncio, web3.py, httpx, FastAPI + uvicorn. One process.
- H-1 discover rentals by polling `RentalCreated` logs from the deploy block (in chunks;
  public RPC is rate-limited — stay well under 20 rps).
- H-2/H-3 probe `GET <node_url>/health` every 5 s; slot is Up only if every probe in the
  slot returned 200 within 2 s.
- R-2 key for a rental = `keys[rental_id % len(keys)]`; each key has its own nonce tracker.
- H-4 after slot completion send `report_uptime`; explicit gas limit (estimate × 1.2 —
  Monad charges the limit); retry until `end + REPORT_GRACE`; never report an unfinished slot.
- H-5 force-down overrides by (rental_id, slot) through the control API.
- H-6 control API exactly as documented in docs/UI_HANDOFF.md §7, CORS open for localhost.
- H-7 log one line per probe and per tx with the tx hash.
- docker/: a tiny HTTP server image (`GET /health` → 200) plus compose file with
  `node-b` service; `docker stop node-b` must make probes fail.
- Keys only from env (`REPORTER_KEYS=0x..,0x..`). Warn at start if any key < 10 MON.

Deliver runnable instructions in oracle/README.md. Test what you can locally against
titanoboa or an anvil/eth-tester chain before touching testnet.
