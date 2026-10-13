# Interface changelog (contract ↔ UI)

Written by the `interface-sync` agent. Newest on top. **BREAKING** = the UI must change.

## 2026-10-13 — oracle serves only allow-listed renter wallets; report budget (T-018, SPEC H-8/H-9; no contract/ABI change)
- Oracle-side behaviour only. No contract change. ABI regenerated; `git diff --stat shared/abi` is
  empty: no function, event or field added, removed or renamed. Not BREAKING for the ABI. The
  control API shapes are unchanged too (no key added, removed or renamed in `/health`, `/nodes`,
  `/rentals`, `/rentals/{id}`, `force-down`). This replaces the "decided but not implemented"
  note in the entry below: both are implemented now.
- **Renter allow-list (H-8).** The oracle serves a rental only if BOTH hold: the provider has a
  node under `[nodes]` in the oracle config AND the renter wallet is in `[renters] allow` in
  `oracle/config.toml`. A rental failing either gate is absent from `/rentals`, gets 404 on
  `/rentals/{id}` (and on `force-down`), receives no probes and no reports, keeps its slots empty
  on-chain and settles as a **refund to the renter**, even when its provider node is healthy.
  `create_rental` itself stays open to everyone; the chain rejects nobody. An empty list means no
  rental is served.
  - Affects **Rental detail**, **Create rental** (indirectly) and the optional **Oracle panel**.
  - What the teammate must do: **send Sora the renter wallet address(es) used for testing and the
    demo before creating rentals**, so they can be put on the list (the list is read once at
    oracle start; Sora restarts the service after editing it). Keep the "not monitored by the
    oracle" notice for rentals absent from `/rentals` while the API is reachable; the API does not
    say which gate failed, so keep the text generic. No code change is required.
- **Report budget (H-9).** At most `2 × n_slots` report transactions per rental: the first send of
  each slot is never blocked by the budget, re-sends share a pool of `n_slots` more. Once the pool
  is used, a slot that still needs a re-send can stay unreported on-chain, which counts as Down.
  - In the API such a slot shows either `reported: false` / `txHash: null` permanently, or
    `reported: true` with the hash of a transaction that may never confirm. Conversely a slot the
    oracle gave up on can show `reported: false` although an earlier transaction for it landed
    later. There is no field that marks a given-up slot.
  - What the teammate must do: colour slots and count Up from the chain (`get_slots(id)`), never
    from the API's `reported` / `up`. Affects **Rental detail** and the optional **Oracle panel**.
- `docs/UI_HANDOFF.md` §7 updated (doc only): `/rentals` bullet, "İzlenmeyen kiralamalar" block,
  new "Rapor bütçesi" block, `reported` field note.
- Not deployed (`shared/deployments/monad-testnet.json` unchanged, `address: null`).

## 2026-10-13 — two new `create_rental` revert strings and form limits (D-12, SPEC v1.2; ABI unchanged)
- `create_rental` has two new checks. Not BREAKING for the ABI (no function, event or field added,
  removed or renamed; `git diff --stat shared/abi` is empty), but the UI must act on both:
  - C-1.11: `start <= block.timestamp + 2 592 000` (30 days), revert string `start too far`.
  - C-1.12: `interval <= 86 400` (1 day), revert string `interval too long`.
  - Check order: the nine existing checks first, then `start too far`, then `interval too long`.
  - Consequence: a rental ends at most 286 days after creation.
- Both limits are internal constants: they are **not in the ABI** and cannot be read from the
  chain. The numbers are written in `docs/UI_HANDOFF.md` §4.
- Affects the **Create rental** screen. What the teammate must do:
  - Add Turkish messages for `start too far` and `interval too long` (UI_HANDOFF §4 revert table).
  - Validate in the form before sending: slot duration (interval) ≤ 86 400 s. The `start` limit
    matters only if the form ever offers a scheduled start; today's `latest block timestamp + 15`
    never hits it.
- `docs/UI_HANDOFF.md` §7 (doc only, optional **Oracle panel** / **Rental detail** screens): the
  oracle reports only rentals whose provider has a node in its config. Other rentals are absent
  from `/rentals`, their slots stay empty on-chain and they settle as a refund to the renter.
  → When the control API is reachable and a rental is absent from `/rentals`, show a "not
  monitored by the oracle" notice. A renter allow-list and a per-rental report budget are decided
  (D-11) but not implemented yet; when they land, rentals from wallets outside the list will be
  unserved too.
- Not deployed (`shared/deployments/monad-testnet.json` unchanged, `address: null`).

## 2026-10-13 — oracle control API available locally (no contract/ABI change)
- The oracle control API (`oracle/api.py`) now exists and returns the shapes listed in
  `docs/UI_HANDOFF.md` §7. It runs only on the machine that runs the oracle (`127.0.0.1:8787`,
  port override `ORACLE_API_PORT`), has no authentication, and is optional: the UI must still work
  without it. Affects the optional **Oracle panel** screen only.
- No contract change. ABI regenerated; `git diff --stat shared/abi` is empty. No breaking change.
- `docs/UI_HANDOFF.md` §7 clarifications (doc only) — what the teammate must do:
  - Requests are answered only when the `Host` header is `127.0.0.1` or `localhost` (any port);
    any other host gets HTTP 400. CORS allows only `http://localhost:*` and `http://127.0.0.1:*`
    origins. → Call `http://localhost:8787` directly, or make the dev proxy send a local `Host`.
  - `reported` is true from the moment a report tx is sent (or the slot is found on-chain); `up`
    before that is the verdict "if sent now", so an unprobed future slot shows `up: false`.
    → Check `reported` and `probesTotal` before colouring a slot; `get_slots` stays the truth.
  - `txHash` can be null on a reported slot; `lastProbe` can be null; `lastProbe.at` is chain time;
    `balanceMon` is a float in MON cached ~30 s and null when the RPC read failed; `/health.ok`
    only means the last balance read succeeded. → Null-check these fields.
  - `POST /rentals/{id}/force-down`: JSON content type, integer `slots` in `0 <= slot < n_slots`,
    at most 256; unknown id → 404, invalid body → 422. On an already reported slot it returns
    `{ ok: true }` but changes nothing on-chain. → Enable the button only for `reported: false` slots.
  - Rentals whose provider is not in the oracle config are absent from `/rentals` (404 on
    `/rentals/{id}`). → Build the rental list from the chain, not from this API.
- Not deployed yet (`shared/deployments/monad-testnet.json` still has `address: null`); the API
  cannot be run against Monad Testnet until a deploy → mock data (UI_HANDOFF §9) still applies.

## 2026-10-13 — function bodies implemented (ABI unchanged)
- All six external function bodies of `contracts/GpuSlaEscrow.vy` are implemented (SPEC v1.1) and
  tested locally. ABI regenerated; `git diff --stat shared/abi` is empty: no function, event or
  field added, removed or renamed. No breaking change — the UI needs no code change for the ABI.
- `docs/UI_HANDOFF.md` edits (doc only):
  - §2: bodies are implemented and tested locally; still not deployed.
  - §4 revert table: added `transfer failed` (`withdraw` when the receiving address is a contract
    that rejects MON; the credit is kept). Affects the Withdraw button's error message — add a
    Turkish text for it.
  - §4: `not active` also covers an unknown rental id; `report_uptime` arguments filled in
    (`rental_id, slot, up`); oracle-only and constructor revert strings listed for reference.
  - §5: `payout_preview(id)` outputs are unnamed in the ABI (viem returns an array), and an unknown
    id returns `(true, 0x0, 0)` instead of reverting. Affects the rental detail screen — check
    `phase(id) != 0` before showing the preview.
- Not deployed yet (`shared/deployments/monad-testnet.json` still has `address: null`) → mock data
  (UI_HANDOFF §9) still applies.

## 2026-10-01 — v1.1 skeleton (ABI frozen)
- Initial ABI in `shared/abi/GpuSlaEscrow.json`: `create_rental`, `report_uptime`, `settle`,
  `raise_objection`, `finalize`, `withdraw`; views `rentals`, `get_slots`, `phase`,
  `payout_preview`, `credits`, `next_rental_id`, `is_reporter`, `REPORT_GRACE`, `CHALLENGE_WINDOW`.
- Not deployed yet (`shared/deployments/monad-testnet.json` has `address: null`) → use mock data (UI_HANDOFF §9).
