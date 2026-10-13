# Tasks

Tasks are planned from the PRD with /dev-workflow:plan-tasks. Identifiers are never reused.
Status: todo, in-progress, blocked, done.

Owner values follow the delegation table in `CLAUDE.md` (agent names), plus `Sora` and
`teammate` for work only a person can do. Rule IDs (C-, O-, S-, X-, F-, P-, R-, H-, T-)
are from `docs/SPEC.md`. All tasks below were planned against PRD "Last updated:
2026-10-13 — latest decision: D-10" and cover PRD §8 Must Have. Two parts go beyond Must Have
because the oracle build covers SPEC H-1..H-7: the force-down control (PRD §8 Should Have, H-5)
and the control API (optional in SPEC H-6). They are labelled in their tasks so the PRD §8.1
cut order stays usable.

## T-001 — Failing tests for rental creation and uptime reporting (C, O, R)

- **Status:** done
- **Owner:** test-engineer
- **PRD:** §7 (rental agreement creation, escrow deposit, oracle uptime reporting), §9.2, §9.3, §10; SPEC C-1.1..C-1.10, O-1..O-6, R-1, R-3, T-1, T-2, E (revert strings)
- **Decisions:** D-02, D-05
- **Depends on:** none
- **Files:** `tests/conftest.py`, `tests/test_create.py`, `tests/test_report.py`, `tests/COVERAGE.md`
- **Acceptance:**
  - At least one test named `test_<ID>_<what>` for every ID C-1.1..C-1.10 and O-1..O-6, each revert test asserting the exact SPEC §3 E string.
  - Boundary tests: `start == block.timestamp` accepted; `n_slots == 256` accepted and `257` reverts `too many slots`; report at `end + REPORT_GRACE` accepted and at `+1` reverts `reporting closed`; report at exactly slot completion accepted and one second earlier reverts `slot not done`.
  - Backfill of an earlier completed Empty slot is accepted; a duplicate reverts `already reported` and does not change `up_count` / `reported_count`.
  - Two rentals reported by two different reporter keys both succeed (SPEC §6).
  - Success effects are asserted: C-1.10 returned id and id increment, every stored field, contract balance, `RentalCreated` fields; for reports the `get_slots` value (1 / 2), `reported_count`, `up_count` (unchanged on a Down report), `UptimeReported` fields.
  - `pytest -q tests/` collects without error; every failing test fails with a revert reason starting with `TODO`; the 5 view/reporter tests still pass.
  - `tests/COVERAGE.md` maps every C/O/R ID to its test names.
- **Out of scope:** editing `contracts/`; tests for S, X, F, P (T-003). Never weaken a test to make it pass.

## T-002 — Implement `create_rental` and `report_uptime`

- **Status:** done
- **Owner:** contract-engineer
- **PRD:** §7, §9.2, §9.3, §12; SPEC C-1.1..C-1.10, O-1..O-6, R-3, E
- **Decisions:** D-02, D-03, D-05
- **Depends on:** T-001
- **Files:** `contracts/GpuSlaEscrow.vy`
- **Acceptance:**
  - `vyper contracts/GpuSlaEscrow.vy` compiles with Vyper 0.4.3.
  - `pytest -q tests/test_create.py tests/test_report.py tests/test_views.py` passes with no test edited.
  - R-3 is checked by the T-001 isolation test here and by code inspection in T-005.
  - `vyper -f abi contracts/GpuSlaEscrow.vy` output is identical to `shared/abi/GpuSlaEscrow.json` at git HEAD (public interface frozen).
- **Out of scope:** `settle`, `raise_objection`, `finalize`, `withdraw` (T-004); any new function, event or storage variable; editing `tests/`, `shared/`, `docs/`.

## T-003 — Failing tests for settlement, objection, finalization, withdrawal (S, X, F, P) and the SPEC §6 scenarios

- **Status:** done
- **Owner:** test-engineer
- **PRD:** §7 (permissionless settlement trigger, deterministic payout, challenge window + objection log, permissionless finalization, withdrawal), §9.1, §9.4, §9.5, §11, §15, §19; SPEC S-1..S-5, X-1..X-4, F-1..F-4, P-1..P-3, T-3, T-4, §6
- **Decisions:** D-01
- **Depends on:** T-002
- **Files:** `tests/test_settle.py`, `tests/test_objection.py`, `tests/test_finalize_withdraw.py`, `tests/test_scenarios.py`, `tests/COVERAGE.md`, helper contracts under `tests/` if needed
- **Acceptance:**
  - At least one test named `test_<ID>_<what>` for every ID S-1..S-5, X-1..X-4, F-1..F-4, P-1..P-3, with exact revert strings.
  - Timing edges on both sides: `settle` at `end + REPORT_GRACE` reverts `too early` and at `+1` succeeds; `raise_objection` at `proposed_at + CHALLENGE_WINDOW - 1` succeeds and at `proposed_at + CHALLENGE_WINDOW` reverts `window closed`; `finalize` at `proposed_at + CHALLENGE_WINDOW - 1` reverts `window open` and at the boundary succeeds.
  - SPEC §6 scenarios each have a test: full compliant run (provider withdraws exactly `price`); full non-compliant run (renter refunded); boundary `100*M == threshold*N` is compliant; unreported slots count as down; objection by each party has no effect on payee or amount; settle and finalize by a third wallet; same result when `settle` is called much later; double `settle` / `finalize` / `withdraw` revert; one address credited by two finalized rentals before withdrawing receives the sum (F-4 is `+=`); a payee contract that re-enters `withdraw` gains nothing (P-2); a payee contract that rejects MON fails only its own `withdraw` (`transfer failed`) while `finalize` and another payee's `withdraw` succeed; report after `settle` reverts `not active` (SPEC lists O-2 before O-3).
  - `finalize` leaves the contract balance unchanged (no transfer); contract balance drops by exactly the withdrawn amount on `withdraw`.
  - `SettlementProposed`, `ObjectionRaised`, `SettlementFinalized`, `Withdrawn` fields are asserted in at least one test each.
  - `phase()` is asserted on both sides of `start`, `end`, `end + REPORT_GRACE` and `proposed_at + CHALLENGE_WINDOW`, and after `finalize`; `payout_preview()` before and after `settle`.
  - R-1 bounds: 8 reporters deploy, 9 do not, a zero address reverts `zero reporter`.
  - Every failing new test fails with a revert reason starting with `TODO`; T-001 tests still pass.
  - `tests/COVERAGE.md` maps every SPEC rule ID to its tests and lists no ID without a test.
- **Out of scope:** editing `contracts/`; oracle tests (T-007..T-010).

## T-004 — Implement `settle`, `raise_objection`, `finalize`, `withdraw`

- **Status:** done
- **Owner:** contract-engineer
- **PRD:** §7, §9.1, §9.4, §11, §12, §15; SPEC S-1..S-5, X-1..X-4, F-1..F-4, P-1..P-3, E
- **Decisions:** D-01, D-03
- **Depends on:** T-003
- **Files:** `contracts/GpuSlaEscrow.vy`
- **Acceptance:**
  - `pytest -q tests/` passes completely with no test edited.
  - Ordering rules (Settled before crediting, credit zeroed before the transfer, no external call in `finalize`, no division in compliance) are covered by the T-003 tests and inspected in T-005.
  - `vyper -f abi contracts/GpuSlaEscrow.vy` output is identical to `shared/abi/GpuSlaEscrow.json` at git HEAD.
  - No `TODO` body remains in the contract.
- **Out of scope:** proportional refund, bonded objection, `provider_ack`, any admin or rotation function (PRD §8 Should/Could/Out of Scope).

## T-005 — Security and spec-conformance review of the contract

- **Status:** done
- **Owner:** security-reviewer
- **PRD:** §15; SPEC §3 (all rules), §6
- **Decisions:** D-01, D-02, D-05
- **Depends on:** T-004
- **Files:** none (read-only); findings are fixed through contract-engineer / test-engineer
- **Acceptance:**
  - The reviewer's checklist items 1–8 and 10 are reported with file:line per finding (item 9, oracle keys, is T-013).
  - No Critical or High finding remains open; every fixed finding has a test; `pytest -q tests/` passes after fixes.
  - The reviewer's "Deploy: yes / no" verdict for the contract is written into this task by the orchestrating session when it is marked done.
- **Out of scope:** deploying; oracle key handling is reviewed in T-010.
- **Result (2026-10-13):** no Critical or High finding; contract verdict "Deploy: yes". Medium test gaps (P-2 defences not separable, no cross-function re-entrancy test) closed by test-engineer with mutation checks; `pytest -q tests/` 238 passed. SPEC gaps found here and since decided by the owner (2026-10-13): unbounded `end` → D-12 (T-016, T-017); constructor strings added to SPEC §3 E; oracle gas grief → D-11 (T-018). Deploy check for T-012: bytecode uses transient storage (`@nonreentrant`), so call `withdraw` once on testnet before the demo.

## T-006 — Regenerate the ABI and sync the UI handoff

- **Status:** done
- **Owner:** interface-sync
- **PRD:** §12 (frozen contract↔UI interface)
- **Decisions:** D-01, D-02, D-05
- **Depends on:** T-005
- **Files:** `shared/abi/GpuSlaEscrow.json`, `docs/UI_HANDOFF.md`, `docs/INTERFACE_CHANGELOG.md`
- **Acceptance:**
  - `vyper -f abi contracts/GpuSlaEscrow.vy > shared/abi/GpuSlaEscrow.json` has been run; `git diff --stat shared/abi` is reported.
  - Every function, event and field in the ABI matches `docs/UI_HANDOFF.md` §4–§6; every revert string in the contract appears in UI_HANDOFF §4 (`transfer failed` is the one a UI call can meet that is missing today; the `report_uptime` strings are oracle-only).
  - `docs/INTERFACE_CHANGELOG.md` has a dated entry stating that bodies are implemented and whether the ABI changed.
  - `shared/deployments/monad-testnet.json` is unchanged (`address: null`) — nothing is deployed.
- **Out of scope:** `frontend/`; deploying; changing contract code.

## T-007 — Docker demo node

- **Status:** done
- **Owner:** oracle-engineer
- **PRD:** §7 (health-probe uptime source), §8 Must Have (Docker container), §12 (demo node), §20 (separate nodes per provider); SPEC H-2
- **Decisions:** D-04, D-10
- **Depends on:** T-006 (build order only: the oracle starts after the contract pipeline)
- **Files:** `docker/` (server, Dockerfile, compose file), `oracle/README.md` (run section)
- **Acceptance:**
  - `docker compose -f docker/docker-compose.yml up -d --build` starts two services, `node-a` and `node-b`, each answering `GET /health` with HTTP 200 on its own published localhost port.
  - After `docker stop` of one node its `/health` request fails (connection error or timeout within 2 s) while the other still returns 200; `docker start` restores 200.
  - With both nodes up, the T-008 probe code run against the real containers logs successes; after `docker stop node-b` it logs failures for that node only (checked once T-008 exists; recorded in T-013).
  - The image has no dependency beyond a stock Python (or equally small) base image.
- **Out of scope:** any real GPU workload; Chainlink CRE in any form (D-10). The implementer decides ports and container names beyond `node-a` / `node-b`.

## T-008 — Oracle: health probing and per-slot verdict (H-2, H-3, H-5, H-7)

- **Status:** done
- **Owner:** oracle-engineer
- **PRD:** §7 (health-probe uptime source; force-down backup — Should Have, §8), §10 ("what up means"); SPEC H-2, H-3, H-5, H-7
- **Decisions:** D-04 (incl. clarification 2026-10-13: a slot with zero probes is Down)
- **Depends on:** T-006 (build order only)
- **Files:** `oracle/` (probe + slot-verdict modules, `config.example.toml`), `oracle/tests/`
- **Acceptance (each by a test in `oracle/tests/`, no network needed):**
  - A slot with at least one probe, all HTTP 200 within 2 s, is Up.
  - A slot with **zero** probes is Down (never Up).
  - A slot with one failed probe among successes is Down; non-200, timeout over 2 s and connection error each count as a failed probe.
  - A force-down mark on (rental, slot) makes the verdict Down even when all probes succeeded; clearing it restores the probe verdict for slots not yet reported.
  - A probe is attributed to the slot whose interval `[start + k*interval, start + (k+1)*interval)` contains its time; probes before `start` or at/after `end` belong to no slot.
  - Provider address → node URL comes from `oracle/config.toml`; a rental whose provider has no configured node gets no probes and is not tracked (see T-009).
  - Time is an input: the verdict code takes the probe's timestamp from its caller and reads no clock itself; the service passes chain time (T-009), so probes and slot completion share one time base.
  - Every probe writes one stdout log line (provider/url, ok, latency).
- **Out of scope:** sending transactions (T-009); the HTTP control API (T-010). The implementer decides internal data structures. Code uses no syntax or stdlib newer than Python 3.11 (the local venv is 3.14; no 3.11 interpreter is installed to check this by command).

## T-009 — Oracle: rental discovery and report submission (H-1, H-4, R-2)

- **Status:** done
- **Owner:** oracle-engineer
- **PRD:** §10, §12 (oracle service), §13 (gas charged on the limit, reserve balance); SPEC H-1, H-4, R-2, O-3, O-5
- **Decisions:** D-02, D-04
- **Depends on:** T-006, T-008
- **Files:** `oracle/` (chain client, reporter loop, entry point), `oracle/tests/`, `.env.example`
- **Acceptance (tests run against a local in-process chain running the compiled contract, with time travel instead of real waiting — no testnet, no funded or real key; signing in tests uses keys generated inside the test):**
  - Rentals are discovered from `RentalCreated` logs polled from the configured deploy block, in bounded block chunks.
  - The reporter key for a rental is `keys[rental_id % len(keys)]`; reports for two rentals with different ids mod `len(keys)` are sent from two different addresses.
  - A slot is reported only after it completed by **chain time** (latest block timestamp), never by the local clock; no report is attempted for an unfinished slot.
  - Each report transaction carries an explicit gas limit derived from an estimate (× 1.2), not a node default.
  - A failed send is retried until `end + REPORT_GRACE` and not after; an `already reported` slot is treated as done.
  - Every sent transaction logs its hash to stdout; private keys are read only from the environment (`REPORTER_KEYS`) and never logged.
  - A rental whose provider has no node in `oracle/config.toml` is ignored: no probes and no report transactions, so a stranger's rental cannot spend reporter gas. Its slots stay Empty, which `settle` counts as Down (same payout as reporting Down). Accepted by the owner as D-13 (2026-10-13).
  - At start the service warns for any reporter key holding less than 10 MON (CLAUDE.md hard rule).
- **Out of scope:** deploying the contract; using any real private key; per-rental key binding on-chain; key failover.

## T-010 — Oracle: control API (H-6)

- **Status:** done
- **Owner:** oracle-engineer
- **PRD:** §7 (force-down backup control — Should Have, §8); SPEC H-5, H-6 (optional for the UI); `docs/UI_HANDOFF.md` §7
- **Decisions:** D-04
- **Depends on:** T-008, T-009
- **Files:** `oracle/` (FastAPI app), `oracle/tests/`
- **Acceptance:**
  - `GET /health`, `GET /nodes`, `GET /rentals`, `GET /rentals/{id}`, `POST /rentals/{id}/force-down`, `DELETE /rentals/{id}/force-down` return the shapes in `docs/UI_HANDOFF.md` §7, tested with FastAPI's test client.
  - `POST …/force-down` with `{"slots":[2,3]}` makes the T-008 verdict for those slots Down; `DELETE` clears it; an unknown rental id returns 404.
  - CORS allows localhost origins; default port 8787.
  - `pytest -q oracle/tests/` passes.
- **Out of scope:** exposing the API beyond localhost; authentication; `frontend/`.

## T-011 — Demo interface: frontend against the frozen ABI

- **Status:** todo
- **Owner:** teammate
- **PRD:** §7 (minimal frontend, P1), §8 Must Have (demo interface), §12; `docs/UI_HANDOFF.md`
- **Decisions:** D-01
- **Depends on:** T-006 to build against the ABI; T-012 (deployed address) for the acceptance run
- **Files:** `frontend/` (teammate only — agents never write here)
- **Acceptance:**
  - A user completes the PRD §6 journey in the UI: connect wallet, create agreement, see slots fill, `settle` and `finalize` from any connected wallet, `withdraw` for the payee.
- **Out of scope:** everything outside `frontend/`. If the frontend slips, the PRD §8 fallback is a `cast`/script demo narrated over the explorer; that fallback is T-014.

## T-012 — Testnet deploy and funding

- **Status:** blocked
- **Owner:** Sora
- **PRD:** §8 Must Have (contract on Monad Testnet), §13, §21 (funding and testnet risks)
- **Decisions:** D-03, D-06
- **Depends on:** T-006, T-013, T-014, T-017, T-018. Waits for: Sora — needs funded testnet keys in `.env`; agents do not deploy and use no private key in this build.
- **Files:** `shared/deployments/monad-testnet.json` and `docs/INTERFACE_CHANGELOG.md` (via interface-sync after the deploy)
- **Acceptance:**
  - `pytest -q tests/` passes on the deployed commit; the contract is deployed with `scripts/deploy.py` (T-014), which writes the deployment file, and verified on a Monad explorer; interface-sync then checks the file and updates the handoff docs. Commit first, so the recorded commit is not `-dirty`.
  - Balances checked before the run: the renter wallet keeps ≥ 10 MON after its payable `create_rental` (reserve rule applies to value spends only, PRD §13); every other EOA has enough MON for gas.
- **Out of scope:** Chainlink CRE (D-10); mainnet; real funds.

## T-013 — Oracle: local end-to-end run and key-handling review

- **Status:** done
- **Owner:** oracle-engineer
- **PRD:** §19, §20; SPEC §5, H-1..H-7
- **Decisions:** D-02, D-04, D-10
- **Depends on:** T-004, T-007, T-009, T-010
- **Files:** `oracle/tests/`, `oracle/README.md`
- **Acceptance:**
  - End-to-end test with the compiled contract on a local in-process chain, keys generated inside the test, a stub health server and time travel (no real waiting), using the SPEC §5 parameters: (a) node healthy for all 4 slots → 4 Up reports → `settle` compliant → provider credited; (b) node failing for 2 slots → `up_count == 2` → refund to renter; (c) force-down of 2 slots with a healthy node → refund to renter; (d) the service runs no probe in a slot → that slot is reported Down.
  - Two rentals with ids mapping to different keys are reported by two different senders in the same run.
  - Real-container check recorded: with `node-a` and `node-b` from T-007 running, the probe loop logs successes; after `docker stop node-b` it logs failures for `node-b` only.
  - `pytest -q oracle/tests/` and `pytest -q tests/` both pass.
  - security-reviewer checklist item 9 (keys only from env, never logged, `.env` git-ignored) has no Critical or High finding open.
  - `oracle/README.md` gives the commands to start the nodes and the service on the team's WSL machine.
- **Out of scope:** testnet runs; any funded key.
- **Result (2026-10-13):** `pytest -q oracle/tests/` 93 passed, `pytest -q tests/` 238 passed; real-container check passed. Key-handling review: pass, no Critical; Medium/Low code findings fixed with tests (Host check, gas and fee caps, same-nonce replacement, config validation). Spam-rental finding (High) decided as D-11; implementation is T-018. To check on testnet in T-012: real `report_uptime` gas estimate against `GAS_CAP` (300,000), Monad's fee-replacement rule, `eth_getLogs` chunk size, same-block landing of two keys' reports.

## T-014 — Deploy script and scripted demo driver (fallback demo interface)

- **Status:** in-progress
- **Owner:** contract-engineer (deploy script), oracle-engineer (scripted demo fallback); Sora owns `scripts/` and is the only one who runs them against testnet (CLAUDE.md, 2026-10-13)
- **PRD:** §8 Must Have (demo interface: frontend **or** `cast`/script fallback), §20 (fallback demo path)
- **Decisions:** D-01, D-02
- **Depends on:** T-006, T-017
- **Files:** `scripts/`
- **Acceptance:**
  - Deploy script: reads the RPC URL and keys from environment variables only, deploys the contract with the reporter addresses, prints the address and deploy block, and writes `shared/deployments/monad-testnet.json`; it sets an explicit gas limit and refuses a wrong chain id. Exercised against a local chain only; **not run against testnet by an agent**.
  - Demo driver (not started; planned only if the frontend slips): one script drives the PRD §20 sequence (create, wait, third-wallet `settle`, `raise_objection`, `finalize`, `withdraw`) with explicit gas limits, printing each transaction hash; exercised against a local chain.
- **Out of scope:** running either against testnet by an agent.
- **Result (2026-10-13):** deploy script done — `scripts/deploy.py`, `pytest -q scripts/` 35 passed on a local chain; reviewed (gas and fee caps, early tx-hash print added). Never run against a network. The task stays in-progress: the scripted demo driver is not written.

## T-015 — Demo rehearsal on testnet

- **Status:** blocked
- **Owner:** Sora
- **PRD:** §19, §20, §21 (single-host, funding and testnet risks), §8.1 (backup video)
- **Decisions:** D-02, D-06, D-09, D-10
- **Depends on:** T-012, T-013, and T-011 or T-014. Waits for: Sora — testnet keys and a deployed contract.
- **Files:** none
- **Acceptance (PRD §19):**
  - Both PRD §20 runs complete on testnet; `settle` and `finalize` are sent by a third wallet; reports for two rentals come from two reporter keys and land in the same block, visible as two senders.
  - `raise_objection` emits its event and the credited payout is unchanged; the payee's `withdraw` transfers exactly the credited amount and a second `withdraw` reverts.
  - `docker stop` of one node for at least two slots produces the renter refund.
  - Checked before the run: WSL machine kept awake, Docker daemon and both nodes started, the network reaches the public RPC; Monad numbers re-checked (D-06); a backup video is recorded.
  - The track "Trust, Identity & AI Infrastructure" is selected on the platform after re-checking the track list (D-09).
- **Out of scope:** Chainlink CRE (D-10); mainnet; real funds.

## T-016 — Failing tests for the creation bounds (C-1.11, C-1.12)

- **Status:** done
- **Owner:** test-engineer
- **PRD:** §7 (rental agreement creation), §9.2, §15; SPEC C-1.11, C-1.12, E. Planned against PRD "latest decision: D-13".
- **Decisions:** D-12
- **Depends on:** T-004
- **Files:** `tests/test_create.py`, `tests/test_scenarios.py`, `tests/COVERAGE.md`
- **Acceptance:**
  - `start == now + 30 days` accepted, `+1` reverts `start too far`; `interval == 86400` accepted, `86401` reverts `interval too long`.
  - The largest allowed rental (start + 30 days, interval 86400, 256 slots) is created, its views return, and `settle` succeeds after its grace period.
  - `end = 2**256 - 1` reverts with a SPEC §3 E string, not an arithmetic panic.
  - New tests fail only because the two checks are not implemented; all other tests pass.
- **Out of scope:** editing `contracts/`.

## T-017 — Implement the creation bounds and sync the interface docs

- **Status:** done
- **Result (2026-10-13):** `pytest -q tests/` 253 passed; ABI unchanged; security-reviewer: no Critical or High, contract verdict "Deploy: yes"; check order pinned by `test_C_order_*` (four mutants killed); `docs/UI_HANDOFF.md` §4 and `docs/INTERFACE_CHANGELOG.md` updated.
- **Owner:** contract-engineer, then security-reviewer, then interface-sync
- **PRD:** §7, §9.2, §12, §15; SPEC C-1.11, C-1.12, check order
- **Decisions:** D-12
- **Depends on:** T-016
- **Files:** `contracts/GpuSlaEscrow.vy`; `docs/UI_HANDOFF.md`, `docs/INTERFACE_CHANGELOG.md`, `shared/abi/GpuSlaEscrow.json` (interface-sync)
- **Acceptance:**
  - `pytest -q tests/` passes with no test edited; checks run in the SPEC order.
  - ABI unchanged (both constants are internal).
  - security-reviewer reports no Critical or High on the change.
  - `docs/UI_HANDOFF.md` §4 lists `start too far` and `interval too long` and the form limits (slot duration ≤ 86,400 s; start ≤ 30 days ahead); `docs/INTERFACE_CHANGELOG.md` has the entry.
- **Out of scope:** a pre-start cancel (Future).

## T-018 — Oracle: renter allow-list and per-rental report budget

- **Status:** done
- **Result (2026-10-13):** tests first (20 new tests red, then green); `pytest -q oracle/tests/` 117 passed, `pytest -q tests/` 253, `pytest -q scripts/` 35. Reading of "cannot be below N" applied: each slot's first send reserved, N shared re-submissions — to be confirmed by the owner. Known side effect: once re-submissions are spent, a stuck transaction is no longer replaced, so later reports from the same reporter key queue behind its nonce.
- **Owner:** oracle-engineer
- **PRD:** §10 ("Which rentals the service reports"), §15 (reporter gas griefing), §21; SPEC H-8, H-9
- **Decisions:** D-11, D-13
- **Depends on:** T-013. (The budget question was answered on 2026-10-13: D-11 clarification — budget = 2 × N, re-submissions count, never below N; SPEC H-8, H-9.)
- **Files:** `oracle/` (config, service, tests, README), `oracle/config.example.toml`
- **Acceptance:**
  - A rental whose renter is not on the allow-list in `oracle/config.toml` is ignored at discovery: no probes, no `get_slots` call, no transaction; one log line.
  - A listed renter's rental is reported; address matching is case-insensitive; an invalid address in the list fails at start.
  - The service broadcasts at most `2 * n_slots` report transactions per rental: each slot's first send is always allowed, re-submissions (retry or fee replacement) share `n_slots` more; a send refused before broadcast does not count; one log line when the re-submissions are spent.
  - End-to-end demo scenarios still pass with the demo renter on the list.
  - `docs/UI_HANDOFF.md` §7 says that unserved rentals do not appear in `/rentals` (interface-sync).
- **Out of scope:** any on-chain restriction on who may create a rental.

