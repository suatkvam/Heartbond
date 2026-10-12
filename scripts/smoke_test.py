"""
Day-0 smoke test for Monad Testnet (run BEFORE writing real contract code).

What it proves:
  1. Vyper output deploys and runs on Monad Testnet (reviewer risk #3)
  2. Events are emitted and readable via RPC (the UI depends on this)
  3. Real block time / timestamp sharing, measured live (reviewer risk #2)

Usage:
  pip install web3 vyper
  export MONAD_RPC=https://testnet-rpc.monad.xyz
  export DEPLOYER_KEY=0x...            # faucet-funded testnet key, never a real one
  python scripts/smoke_test.py
Then verify Hello.vy on the explorer (see docs/DAY0_CHECKLIST.md step 4).
"""
import json
import os
import statistics
import subprocess
import sys

from web3 import Web3

RPC = os.environ.get("MONAD_RPC", "https://testnet-rpc.monad.xyz")
CHAIN_ID = 10143


def compile_vy(path: str) -> tuple[list, str]:
    out = subprocess.check_output(["vyper", "-f", "abi,bytecode", path], text=True)
    abi_line, bytecode = out.strip().split("\n")
    return json.loads(abi_line), bytecode


def send(w3: Web3, acct, tx: dict) -> dict:
    tx.setdefault("from", acct.address)
    tx["nonce"] = w3.eth.get_transaction_count(acct.address)
    tx["chainId"] = CHAIN_ID
    # Monad charges the gas LIMIT, not gas used -> keep it tight (+20%).
    tx["gas"] = int(w3.eth.estimate_gas(tx) * 1.2)
    if "maxFeePerGas" not in tx and "gasPrice" not in tx:
        tx["gasPrice"] = w3.eth.gas_price
    signed = acct.sign_transaction(tx)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    rcpt = w3.eth.wait_for_transaction_receipt(h, timeout=60)
    assert rcpt["status"] == 1, f"tx reverted: {h.hex()}"
    return rcpt


def measure_blocks(w3: Web3, n: int = 40) -> None:
    head = w3.eth.block_number
    blocks = [w3.eth.get_block(head - i) for i in range(n)][::-1]
    ts = [b["timestamp"] for b in blocks]
    span = ts[-1] - ts[0]
    per_ts: dict[int, int] = {}
    for t in ts:
        per_ts[t] = per_ts.get(t, 0) + 1
    print(f"[blocks] {n} blocks over {span}s -> ~{span * 1000 / (n - 1):.0f} ms/block")
    print(f"[blocks] blocks sharing one timestamp: median {statistics.median(per_ts.values())}, max {max(per_ts.values())}")
    print(f"[blocks] latest block gasLimit: {blocks[-1]['gasLimit']:,}")


def main() -> int:
    w3 = Web3(Web3.HTTPProvider(RPC))
    assert w3.eth.chain_id == CHAIN_ID, f"wrong chain {w3.eth.chain_id}"
    acct = w3.eth.account.from_key(os.environ["DEPLOYER_KEY"])
    bal = w3.from_wei(w3.eth.get_balance(acct.address), "ether")
    print(f"[wallet] {acct.address} balance {bal} MON")
    if bal < 10:
        print("[wallet] WARNING: below the 10 MON default reserve balance — fund more before the demo")

    measure_blocks(w3)

    abi, bytecode = compile_vy("contracts/Hello.vy")
    rcpt = send(w3, acct, w3.eth.contract(abi=abi, bytecode=bytecode).constructor().build_transaction({"from": acct.address}))
    addr = rcpt["contractAddress"]
    print(f"[deploy] Hello deployed at {addr} (gas used {rcpt['gasUsed']})")

    hello = w3.eth.contract(address=addr, abi=abi)
    rcpt = send(w3, acct, hello.functions.greet().build_transaction({"from": acct.address}))
    logs = hello.events.Greeted().process_receipt(rcpt)
    assert logs and logs[0]["args"]["count"] == 1, "event missing"
    assert hello.functions.greetings().call() == 1
    print(f"[event] Greeted(count=1) seen in block {rcpt['blockNumber']}")
    print(f"[ok] Vyper works on Monad Testnet. Now verify {addr} on the explorer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
