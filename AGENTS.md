# Agent rules (UI work)
- Work only in frontend/. Never edit contracts/, oracle/, scripts/, tests/, shared/ or docs/.
- Source of truth for the UI: docs/UI_HANDOFF.md, docs/INTERFACE_CHANGELOG.md, shared/abi/GpuSlaEscrow.json, shared/deployments/monad-testnet.json.
- If the UI needs a contract change, stop and tell Sora; do not change the ABI.
- No private keys in frontend code or env; only public config (RPC, chain id 10143, contract address) via VITE_ vars.
