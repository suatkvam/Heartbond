# Interface changelog (contract ↔ UI)

Written by the `interface-sync` agent. Newest on top. **BREAKING** = the UI must change.

## 2026-10-01 — v1.1 skeleton (ABI frozen)
- Initial ABI in `shared/abi/GpuSlaEscrow.json`: `create_rental`, `report_uptime`, `settle`,
  `raise_objection`, `finalize`, `withdraw`; views `rentals`, `get_slots`, `phase`,
  `payout_preview`, `credits`, `next_rental_id`, `is_reporter`, `REPORT_GRACE`, `CHALLENGE_WINDOW`.
- Not deployed yet (`shared/deployments/monad-testnet.json` has `address: null`) → use mock data (UI_HANDOFF §9).
