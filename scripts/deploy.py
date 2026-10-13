"""
Deploy GpuSlaEscrow to Monad Testnet and write shared/deployments/monad-testnet.json.

Run by Sora only; agents never run this against testnet.

Usage:
  export MONAD_RPC=https://testnet-rpc.monad.xyz
  export DEPLOYER_KEY=0x...                 # faucet-funded testnet key, never a real one
  export REPORTER_KEYS=0x...,0x...          # and/or REPORTER_ADDRESSES=0x...,0x...
  python scripts/deploy.py [--force]

Environment variables (the only inputs):
  MONAD_RPC           required, no default.
  DEPLOYER_KEY        required. Private key that pays for the deploy.
  REPORTER_KEYS       comma-separated private keys; the reporter ADDRESSES are derived
                      from them (SPEC R-1: 1..8, no duplicates, no zero address).
  REPORTER_ADDRESSES  comma-separated addresses; alternative to REPORTER_KEYS so this
                      machine does not need the reporter keys. If both are set they
                      must describe the same addresses.
  --force             overwrite a deployment file that already has an address.

Only chain id 10143 (Monad Testnet) is accepted; there is no mainnet path.
The compiled ABI must equal shared/abi/GpuSlaEscrow.json (else run interface-sync first).

After deploying: `withdraw` uses transient storage (EIP-1153) for its re-entrancy lock.
Do one full rental + `withdraw` on testnet before the demo (not done by this script).
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from web3 import Web3
from web3.exceptions import TimeExhausted

from smoke_test import compile_vy

ROOT = Path(__file__).resolve().parent.parent
CONTRACT = ROOT / "contracts" / "GpuSlaEscrow.vy"
ABI_PATH = ROOT / "shared" / "abi" / "GpuSlaEscrow.json"
OUT_PATH = ROOT / "shared" / "deployments" / "monad-testnet.json"
CHAIN_ID = 10143
MAX_REPORTERS = 8
ZERO = "0x" + "00" * 20
# Caps checked before signing (never clamped: over the cap -> refuse and let a human look).
# Measured on eth-tester 2026-10-13: constructor estimate 1,451,670 gas with 1 reporter,
# 1,614,410 with 8 -> the limit we send (+20%) is at most 1,937,292. Cap = ~2x that.
GAS_CAP = 4_000_000
MAX_FEE_PER_GAS_WEI = 1000 * 10**9  # 1000 gwei; Monad's minimum base fee is 100 gwei
# Worst-case deploy fee at both caps (4 MON); below this the wallet may not cover the gas.
LOW_GAS_BALANCE_WEI = GAS_CAP * MAX_FEE_PER_GAS_WEI


def check_reporters(addresses) -> list[str]:
    """Checksummed reporter list, or exit. Mirrors the constructor + SPEC R-1."""
    if not 1 <= len(addresses) <= MAX_REPORTERS:
        raise SystemExit(f"need 1..{MAX_REPORTERS} reporters, got {len(addresses)}")
    if not all(Web3.is_address(a) for a in addresses):
        raise SystemExit("reporter list contains a malformed address")
    out = [Web3.to_checksum_address(a) for a in addresses]
    if ZERO in out:
        raise SystemExit("reporter list contains the zero address")
    if len(set(out)) != len(out):
        raise SystemExit("reporter list contains a duplicate")
    return out


def git_commit() -> str:
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()

    sha = git("rev-parse", "HEAD")
    if git("status", "--porcelain"):
        print("[git] WARNING: uncommitted changes -> commit recorded with a -dirty suffix")
        sha += "-dirty"
    return sha


def deploy(w3, deployer_account, reporter_addresses, out_path, expected_chain_id=CHAIN_ID, force=False) -> dict:
    """Deploy and write `out_path`. Every refusal happens before a transaction is sent."""
    try:
        chain_id = w3.eth.chain_id
    except Exception:
        # `from None`: the library's message (and traceback) contains the RPC URL.
        raise SystemExit("cannot reach MONAD_RPC (value not shown)") from None
    if chain_id != expected_chain_id:
        raise SystemExit(f"wrong chain id {chain_id}, expected {expected_chain_id}")
    reporters = check_reporters(reporter_addresses)

    out_path = Path(out_path)
    if out_path.exists() and not force:
        try:
            existing = json.loads(out_path.read_text())
        except ValueError:
            existing = None
        if not isinstance(existing, dict):
            raise SystemExit(f"{out_path} is not a deployment record (not a JSON object); pass --force to overwrite")
        if existing.get("address"):
            raise SystemExit(
                f"{out_path} already records a deployment ({existing['address']}); pass --force to overwrite"
            )

    abi, bytecode = compile_vy(str(CONTRACT))
    if abi != json.loads(ABI_PATH.read_text()):
        raise SystemExit(f"compiled ABI differs from {ABI_PATH}: run interface-sync before deploying")
    commit = git_commit()

    sender = deployer_account.address
    bal = w3.eth.get_balance(sender)
    print(f"[wallet] {sender} balance {w3.from_wei(bal, 'ether')} MON")
    if bal < LOW_GAS_BALANCE_WEI:
        print(f"[wallet] WARNING: low gas balance (< {w3.from_wei(LOW_GAS_BALANCE_WEI, 'ether')} MON)")

    ctor = w3.eth.contract(abi=abi, bytecode=bytecode).constructor(reporters)
    tx = {"from": sender, "nonce": w3.eth.get_transaction_count(sender), "chainId": chain_id}
    base_fee = w3.eth.get_block("latest").get("baseFeePerGas")
    if base_fee is None:
        fee = tx["gasPrice"] = w3.eth.gas_price
    else:
        tip = w3.eth.max_priority_fee
        tx["maxPriorityFeePerGas"] = tip
        fee = tx["maxFeePerGas"] = 2 * base_fee + tip
    # Monad charges the gas LIMIT, not gas used -> keep it tight (+20%).
    tx["gas"] = int(ctor.estimate_gas({"from": sender}) * 1.2)
    if tx["gas"] > GAS_CAP:
        raise SystemExit(f"gas limit {tx['gas']} exceeds GAS_CAP {GAS_CAP}; nothing signed or sent")
    if fee > MAX_FEE_PER_GAS_WEI:
        raise SystemExit(f"fee per gas {fee} wei exceeds MAX_FEE_PER_GAS_WEI {MAX_FEE_PER_GAS_WEI}; nothing signed or sent")
    signed = deployer_account.sign_transaction(ctor.build_transaction(tx))
    tx_hex = Web3.to_hex(w3.eth.send_raw_transaction(signed.raw_transaction))
    print(f"[deploy] tx hash      {tx_hex}", flush=True)
    try:
        rcpt = w3.eth.wait_for_transaction_receipt(tx_hex, timeout=120)
    except TimeExhausted:
        raise SystemExit(
            f"no receipt for {tx_hex} after 120 s; the tx may still be mined: "
            "do NOT re-run blindly — check the explorer first"
        ) from None
    if rcpt["status"] != 1:
        raise SystemExit(f"deploy tx reverted: {tx_hex}; deployment file NOT written")
    address = Web3.to_checksum_address(rcpt["contractAddress"])
    print(f"[deploy] address      {address}", flush=True)

    # From here the contract exists: a failure means "deployed at the address above, file NOT written".
    def fail(why):
        raise SystemExit(f"post-deploy check failed: {why} (contract {address}, tx {tx_hex}); deployment file NOT written")

    if len(w3.eth.get_code(address)) == 0:
        fail("no code at the address")
    c = w3.eth.contract(address=address, abi=abi)
    if c.functions.next_rental_id().call() != 1:
        fail("next_rental_id != 1")
    for r in reporters:
        if not c.functions.is_reporter(r).call():
            fail(f"{r} is not allow-listed")

    record = {
        "chainId": chain_id,
        "address": address,
        "deployBlock": rcpt["blockNumber"],
        "reporters": reporters,
        "reportGrace": c.functions.REPORT_GRACE().call(),
        "challengeWindow": c.functions.CHALLENGE_WINDOW().call(),
        "deployedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit": commit,
    }
    out_path.write_text(json.dumps(record, indent=2) + "\n")

    print(f"[deploy] deploy block {rcpt['blockNumber']}")
    print(f"[deploy] reporters    {', '.join(reporters)}")
    print(f"[deploy] gas used     {rcpt['gasUsed']} (limit {tx['gas']})")
    print(f"[deploy] wrote        {out_path}")
    print("[next] withdraw's re-entrancy lock uses transient storage (EIP-1153):")
    print("[next] do one full rental + withdraw on testnet before the demo, then run interface-sync.")
    return record


def _split(value: str) -> list[str]:
    return [p.strip() for p in value.split(",") if p.strip()]


def _account(key: str, var: str):
    try:
        return Web3().eth.account.from_key(key)
    except Exception:
        # `from None`: the library's message may contain the key material.
        raise SystemExit(f"{var} is not a valid private key (value not shown)") from None


def read_env(env) -> tuple[str, object, list[str]]:
    """(rpc url, deployer account, reporter addresses). Errors name the variable only."""
    for var in ("MONAD_RPC", "DEPLOYER_KEY"):
        if not env.get(var):
            raise SystemExit(f"{var} is not set")
    deployer = _account(env["DEPLOYER_KEY"], "DEPLOYER_KEY")

    from_keys = [_account(k, "REPORTER_KEYS").address for k in _split(env.get("REPORTER_KEYS", ""))]
    from_addrs = _split(env.get("REPORTER_ADDRESSES", ""))
    if not all(Web3.is_address(a) for a in from_addrs):
        raise SystemExit("REPORTER_ADDRESSES contains a malformed address (value not shown)")
    from_addrs = [Web3.to_checksum_address(a) for a in from_addrs]
    if not from_keys and not from_addrs:
        raise SystemExit("set REPORTER_KEYS or REPORTER_ADDRESSES")
    if from_keys and from_addrs and set(from_keys) != set(from_addrs):
        raise SystemExit("REPORTER_KEYS and REPORTER_ADDRESSES do not describe the same addresses")
    return env["MONAD_RPC"], deployer, from_keys or from_addrs


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Deploy GpuSlaEscrow to Monad Testnet (chain id 10143).")
    parser.add_argument("--force", action="store_true", help="overwrite an existing deployment file")
    args = parser.parse_args(argv)
    rpc, deployer, reporters = read_env(os.environ)
    deploy(Web3(Web3.HTTPProvider(rpc)), deployer, reporters, OUT_PATH, force=args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
