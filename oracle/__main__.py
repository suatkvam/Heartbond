"""Entry point: `python -m oracle`.

Environment (export it yourself; this process does not read .env):
  MONAD_RPC       RPC URL (required)
  REPORTER_KEYS   comma-separated reporter private keys, testnet only (required)
  ORACLE_CONFIG   provider -> node URL file (default oracle/config.toml)
  LOG_CHUNK       blocks per eth_getLogs call (default 1000; lower it if the RPC refuses)
  ORACLE_API_PORT control API port on 127.0.0.1 (default 8787; docs/UI_HANDOFF.md section 7)
Contract address, deploy block and chain id come from shared/deployments/monad-testnet.json.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import httpx
import uvicorn
from eth_account import Account
from web3 import Web3

from oracle.api import PORT, create_app
from oracle.chain import Chain
from oracle.config import load_nodes
from oracle.service import LOG_CHUNK, Service

ROOT = Path(__file__).resolve().parent.parent
DEPLOYMENT = ROOT / "shared" / "deployments" / "monad-testnet.json"
ABI = ROOT / "shared" / "abi" / "GpuSlaEscrow.json"


def load_deployment(path=DEPLOYMENT) -> dict:
    dep = json.loads(Path(path).read_text())
    if not dep.get("address") or dep.get("deployBlock") is None:
        raise SystemExit(f"oracle: contract is not deployed - {path} has a null address/deployBlock. "
                         "Deploy first (T-012); interface-sync then fills this file.")
    return dep


def main() -> None:
    dep = load_deployment()  # before any network access
    rpc = os.environ.get("MONAD_RPC")
    keys = [k.strip() for k in os.environ.get("REPORTER_KEYS", "").split(",") if k.strip()]
    if not rpc or not keys:
        raise SystemExit("oracle: set MONAD_RPC and REPORTER_KEYS (see .env.example)")
    try:
        accounts = [Account.from_key(k) for k in keys]
    except Exception:
        # `from None`: the original error could echo a malformed key.
        raise SystemExit("oracle: REPORTER_KEYS holds an invalid private key") from None
    try:
        nodes = load_nodes(os.environ.get("ORACLE_CONFIG", ROOT / "oracle" / "config.toml"))
    except ValueError as exc:  # bad address / URL (and TOML syntax errors)
        raise SystemExit(f"oracle: {exc}") from None
    w3 = Web3(Web3.HTTPProvider(rpc))
    chain = Chain(w3, dep["address"], json.loads(ABI.read_text()), accounts)
    if chain.chain_id != dep["chainId"]:
        raise SystemExit(f"oracle: RPC chain id {chain.chain_id} != deployment chain id {dep['chainId']}")
    print(f"oracle contract={dep['address']} deploy_block={dep['deployBlock']} nodes={len(nodes)} "
          f"reporters={[a.address for a in chain.accounts]}", flush=True)
    chain.warn_low_balances()

    async def run() -> None:
        async with httpx.AsyncClient() as http:
            chunk = int(os.environ.get("LOG_CHUNK", LOG_CHUNK))
            svc = Service(chain, nodes, http, dep["deployBlock"], chunk)
            # One process, one event loop: uvicorn serves the control API while the
            # service loop ticks. 127.0.0.1 only - the API has no authentication.
            port = int(os.environ.get("ORACLE_API_PORT", PORT))
            server = uvicorn.Server(uvicorn.Config(create_app(svc), host="127.0.0.1", port=port,
                                                   log_level="warning"))
            loop = asyncio.create_task(svc.run())
            print(f"control-api http://127.0.0.1:{port}", flush=True)
            try:
                await server.serve()  # returns on Ctrl-C / SIGTERM
            finally:
                loop.cancel()

    asyncio.run(run())


if __name__ == "__main__":
    main()
