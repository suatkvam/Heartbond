# GPU SLA Escrow — Monad Metropolis hackathon

On-chain escrow that pays a GPU provider or refunds a renter from per-slot uptime
reports; anyone can trigger settlement; finality is a fixed timeout.
Team of 2: **Sora** owns everything except the UI; **the teammate owns `frontend/`**.

## Source of truth
1. `docs/SPEC.md` — rule IDs (C-, O-, S-, X-, F-, P-, R-, H-, T-). Code must match it.
2. `docs/PRD.md` — reasoning, claims, risks. Read when wording or scope is in question.
   `docs/DECISIONS.md` — why the PRD changed (D-xx). Record changes with `/dev-workflow:decision`.
3. `docs/REVIEW_2026-10-01.txt` — external review; SPEC §9 records what we did about it.
If a request contradicts SPEC, say so and propose a SPEC change first (log it in SPEC §9).

## Repo map and ownership
| Path | Owner | Agents may write? |
|---|---|---|
| `contracts/` | Sora | contract-engineer |
| `tests/` | Sora | test-engineer |
| `oracle/`, `docker/` | Sora | oracle-engineer |
| `scripts/` | Sora | contract-engineer (deploy script), oracle-engineer (scripted demo fallback) — agents write, only Sora runs them against testnet |
| `shared/abi/`, `shared/deployments/`, `docs/UI_HANDOFF.md`, `docs/INTERFACE_CHANGELOG.md` | Sora → teammate | interface-sync only |
| `docs/pitch/`, `README.md` | Sora | pitch-factchecker |
| `frontend/` | **teammate** | **never** — read only |
| `docs/SPEC.md`, `docs/PRD.md` | Sora | only when Sora explicitly asks |

## Stack
- Vyper 0.4.3 contract, tested with titanoboa + pytest (`pytest -q`)
- Oracle: Python 3.11, web3.py, httpx, FastAPI (control API)
- Monad Testnet: chain id 10143, RPC `https://testnet-rpc.monad.xyz`
- Frontend (teammate): viem ≥ 2.40, reads `shared/abi/GpuSlaEscrow.json` + `shared/deployments/monad-testnet.json`

## Commands
- Compile + ABI: `vyper -f abi contracts/GpuSlaEscrow.vy > shared/abi/GpuSlaEscrow.json`
- Tests: `pytest -q tests/`
- Smoke test on testnet: `python scripts/smoke_test.py` (needs `MONAD_RPC`, `DEPLOYER_KEY`)

## Working mode for contracts/
`CONTRACT_MODE: auto`
- `pair` — Sora writes the function bodies. Agents explain the rule IDs, point at the
  exact lines, write/extend tests first, and review Sora's code. Code is written by an
  agent only when Sora says "write it".
- `auto` — contract-engineer implements directly (use when time is short).
Sora changes this line to switch.

## Delegation
| Task | Agent |
|---|---|
| Implement / explain a contract rule | contract-engineer |
| Tests for a rule ID, coverage matrix | test-engineer |
| Oracle service, Docker node, control API | oracle-engineer |
| Review before any deploy | security-reviewer (read-only) |
| Any change to a public function/event/view, any deploy | interface-sync (always last) |
| README, demo script, Q&A, any external number | pitch-factchecker |

Order for a feature: test-engineer (failing tests) → contract-engineer / Sora → `pytest` →
security-reviewer → interface-sync. Never deploy with failing tests.

## Hard rules
- Never touch `frontend/`. If the UI needs something, write it into `docs/UI_HANDOFF.md`
  via interface-sync and tell Sora.
- Public interface (names, argument order, events, `phase` values) is frozen; changing it
  requires interface-sync to regenerate the ABI and append to `docs/INTERFACE_CHANGELOG.md`.
- Monad gotchas: gas is charged on the **gas limit** → always set explicit tight limits;
  the 10 MON reserve balance applies to **value spends** only (PRD §13): the renter's payable
  `create_rental` must leave ≥ 10 MON (or be an "emptying" transaction); zero-value
  transactions (reports, `settle`, `finalize`, `withdraw`) only need gas; public RPC is rate-limited.
- Claims: "permissionless" = anyone can trigger; data comes from team-held reporters.
  Never say trustless oracle, dispute resolution, or "no one else does this".
- Secrets: private keys only in `.env` (git-ignored). Testnet keys only.
- Write code and docs in English; Sora may talk to you in Turkish — answer in Turkish.
