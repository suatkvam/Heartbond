# GPU SLA Escrow — Implementation Spec v1.1

This is the **build spec**. `docs/PRD.md` is the *why* (research, claims, risks);
this file is the *what exactly*: every rule has an ID, every ID needs a test.
If code and this file disagree, this file wins until it is changed on purpose
(and the change is logged in §9).

Contract language: **Vyper 0.4.3** (fallback: Solidity — decided by the day-0
smoke test, §8). Chain: **Monad Testnet, chain id 10143**.

---

## 1. Actors

| Actor | Who in the demo | Can do |
|---|---|---|
| Renter | wallet A | `create_rental` (pays), `raise_objection`, `withdraw` |
| Provider | wallet B | `raise_objection`, `withdraw` |
| Reporter | oracle keys K1..Kn (team) | `report_uptime` |
| Anyone | wallet C (unrelated) | `settle`, `finalize`, all views |

## 2. Constants

| Name | Value | Note |
|---|---|---|
| `REPORT_GRACE` | 30 s | T-2. Demo value, fixed in bytecode |
| `CHALLENGE_WINDOW` | 60 s | T-4. Demo value, fixed in bytecode |
| `MAX_SLOTS` | 256 | C-1.9. Vyper loops must be bounded |
| `MAX_REPORTERS` | 8 | R-1 |
| Status | 0 None, 1 Active, 2 Proposed, 3 Settled | plain `uint8` |
| Slot | 0 Empty, 1 Up, 2 Down | Empty counts as Down at settle |

## 3. Rules

### C — `create_rental(provider, threshold, interval, start, end, spec_ref)` payable
Reverts unless **all** hold:
- C-1.1 `start >= block.timestamp`
- C-1.2 `end > start`
- C-1.3 `interval > 0`
- C-1.4 `(end - start) % interval == 0`
- C-1.5 `1 <= threshold <= 100`
- C-1.6 `provider != empty(address)`
- C-1.7 `provider != msg.sender` (renter ≠ provider)
- C-1.8 `msg.value > 0`; `price := msg.value` (the PRD's `msg.value == price` collapses into this — price *is* the value sent)
- C-1.9 `n_slots = (end - start) / interval <= MAX_SLOTS` *(new vs PRD)*
- C-1.10 On success: id = `next_rental_id`, then increment; status = Active; emit `RentalCreated`; return id. Contract balance grows by exactly `msg.value`.

### O — `report_uptime(rental_id, slot, up)`
Reverts unless **all** hold:
- O-1 `is_reporter[msg.sender]` (any allow-listed reporter, see R)
- O-2 rental status == Active (covers nonexistent ids: status 0)
- O-3 `block.timestamp <= end + REPORT_GRACE`
- O-4 `slot < n_slots`
- O-5 `block.timestamp >= start + (slot + 1) * interval` (slot completed)
- O-6 slot is Empty (duplicate → revert, never overwrite)
On success: store 1/2, `reported_count += 1`, `up_count += 1` if up, emit `UptimeReported`.
Backfill of any completed Empty slot is allowed until `end + REPORT_GRACE`.

### S — `settle(rental_id)` — anyone
- S-1 status == Active
- S-2 `block.timestamp > end + REPORT_GRACE` (strict)
- S-3 `compliant := 100 * up_count >= threshold * n_slots` (boundary passes)
- S-4 status := Proposed, `proposed_at := block.timestamp`, store `compliant`
- S-5 emit `SettlementProposed(up_count, n_slots, compliant, payee, price, proposed_at, msg.sender)`; payee = provider if compliant else renter. Result is identical for any caller/any later time.

### X — `raise_objection(rental_id)`
- X-1 status == Proposed
- X-2 `block.timestamp < proposed_at + CHALLENGE_WINDOW`
- X-3 caller is the renter or the provider of this rental
- X-4 caller's own flag not yet set (second call reverts); set it, emit `ObjectionRaised`. Changes nothing else.

### F — `finalize(rental_id)` — anyone
- F-1 status == Proposed
- F-2 `block.timestamp >= proposed_at + CHALLENGE_WINDOW`
- F-3 status := Settled **before** crediting
- F-4 `credits[payee] += price`; emit `SettlementFinalized`. **No external call** — objections have zero effect.

### P — `withdraw()` — pull payment *(new vs PRD, reviewer #4)*
- P-1 amount = `credits[msg.sender]`; revert if 0
- P-2 `credits[msg.sender] := 0` before sending (CEI) + `@nonreentrant`
- P-3 `send`/`raw_call` the amount to `msg.sender`; revert if transfer fails (only that caller's own withdraw fails — nobody else's funds are blocked); emit `Withdrawn`

### R — Reporters *(new vs PRD, reviewer #1)*
- R-1 Constructor takes 1..8 reporter addresses; fixed forever (no admin, no rotation).
- R-2 The oracle service sends each rental's reports from a key chosen deterministically (`key = keys[rental_id % len(keys)]`), so reports for different rentals use independent nonces and can land in the same block.
- R-3 `report_uptime` writes only per-rental storage (`rentals[id]`, `_slots[id]`). No global counter is ever written on the report path — keeps reports for different rentals free of storage conflicts.
- **Honesty line (must appear in pitch):** all reporter keys are team-held. This removes the single-*nonce* bottleneck, **not** the single *trust root*.

### V — Views (UI helpers, already implemented in the skeleton)
- `rentals(id)`, `get_slots(id)`, `phase(id)`, `payout_preview(id)`, `credits(addr)`, `next_rental_id()`, `is_reporter(addr)`, `REPORT_GRACE()`, `CHALLENGE_WINDOW()`.
- `phase`: 0 None · 1 Scheduled · 2 Running · 3 Grace · 4 Settleable · 5 Challenge · 6 Finalizable · 7 Settled.

### E — Revert strings (fixed; the UI maps them to messages)
| Rule | String | Rule | String |
|---|---|---|---|
| C-1.1 | `start in past` | O-1 | `not reporter` |
| C-1.2 | `end before start` | O-2 / S-1 | `not active` |
| C-1.3 | `zero interval` | O-3 | `reporting closed` |
| C-1.4 | `not multiple` | O-4 | `bad slot` |
| C-1.5 | `bad threshold` | O-5 | `slot not done` |
| C-1.6 | `zero provider` | O-6 | `already reported` |
| C-1.7 | `renter is provider` | S-2 | `too early` |
| C-1.8 | `no value` | X-1 / F-1 | `not proposed` |
| C-1.9 | `too many slots` | X-2 | `window closed` |
| P-1 | `nothing to withdraw` | X-3 | `not a party` |
| P-3 | `transfer failed` | X-4 | `already objected` |
| | | F-2 | `window open` |

### T — Timing summary
- T-1 slot k = `[start + k·interval, start + (k+1)·interval)`
- T-2 reporting closes `<= end + REPORT_GRACE`; T-3 `settle` opens `> end + REPORT_GRACE` → never overlap
- T-4 `finalize` opens `>= proposed_at + CHALLENGE_WINDOW`; objection closes `< proposed_at + CHALLENGE_WINDOW`

## 4. Oracle service (off-chain, Python)

- H-1 Discovers rentals from `RentalCreated` events (poll from deploy block).
- H-2 Each provider address maps to a node URL in `oracle/config.toml` (demo: a Docker container exposing `GET /health`).
- H-3 Probes the node every 5 s during a slot. **Slot = Up iff at least one probe ran in that slot and every probe that ran returned HTTP 200 within 2 s; a slot with no probe is Down** *(D-04, clarified 2026-10-13: a slot with zero probes must never be reported Up; `docker stop` mid-slot → that slot Down)*.
- H-4 After slot completion, submits `report_uptime` from the R-2 key, explicit tight gas limit, retries until `end + REPORT_GRACE`.
- H-5 Force-down override (backup if Docker fails on stage): marks chosen slots Down regardless of probes.
- H-6 Small HTTP control API (see `docs/UI_HANDOFF.md` §7). Optional for the UI.
- H-7 Logs every probe and tx hash to stdout — this log is shown in the demo video.

## 5. Demo parameters (from PRD §20, unchanged)
interval 30 s, N = 4 (120 s), threshold 75, start = now + 15 s, price 0.01 MON.
Compliant: M=4 or 3 → pass. Non-compliant: `docker stop` the node for ≥ 2 slots → M ≤ 2 → refund.
A third wallet calls `settle` and `finalize`; each payee then calls `withdraw`.

## 6. Test matrix (every ID ↔ at least one test)
Tests live in `tests/`, named `test_<ID>_<what>` (e.g. `test_C_1_4_duration_not_multiple_reverts`).
Must also cover: full compliant run, full non-compliant run, boundary `100M == threshold·N`,
objection has no effect on payout, settle by third wallet, double settle/finalize/withdraw revert,
withdraw by a contract that rejects MON fails only for itself, reports for 2 rentals from 2 keys.

## 7. Pitch-critical claims (do not drift)
- "Permissionless" = anyone can **trigger** `settle`/`finalize`. Not trustless data.
- "Objection log", "timeout finality" — never "dispute resolution".
- Never "no one else does this" (Aethir overlap, PRD §18).
- Every Monad number in slides/README: quoted with source URL + date checked.
  Checked 2026-10-01 on docs.monad.xyz/developer-essentials/summary: 300 ms blocks,
  finality after 2 blocks (600 ms), 3–4 blocks share a timestamp, 30M tx / 150M block gas.
  (The reviewer quoted 400/800/2–3/200M — not what that page says today. Re-measure with
  `scripts/smoke_test.py` and quote the page as it reads on demo day.)

## 8. Day-0 gates (before the real contract)
- G-1 `scripts/smoke_test.py` passes on Monad Testnet (Vyper deploy + event + block measurement).
- G-2 Hello.vy verified on an explorer (Sourcify / MonadVision or Monadscan).
- G-3 If G-1 or G-2 fails and can't be fixed in ~2 h → switch to Solidity, same spec, same ABI names.

## 9. Changes vs PRD (rev 2026-09-27)
| ID | Change | Why |
|---|---|---|
| P-* | Pull payment: `finalize` credits, `withdraw` pays | Reviewer #4 — a rejecting recipient could lock funds |
| R-* | 1..8 reporter keys, per-rental key choice, no global writes on report path | Reviewer #1 — single nonce serializes reports |
| C-1.9 | `n_slots <= 256` | Vyper bounded loops |
| C-1.8 | `price := msg.value` | Removes a redundant parameter |
| H-* | Oracle probes a real Docker health endpoint; force-down kept as backup | Reviewer demo suggestion |
| §7 | Monad numbers re-checked against live docs | Reviewer #2 |
| H-3 | Zero-probe slot is Down (D-04 clarification, 2026-10-13) | Review 2026-10-13: "every probe succeeded" was vacuously true with no probes |
| — | Provider consent still not on-chain; stated proactively in demo narration | Reviewer #5 (Could-Have: non-gating `provider_ack` event) |
