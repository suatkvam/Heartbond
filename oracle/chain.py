"""web3 wrapper for the GpuSlaEscrow contract (SPEC H-1, H-4, R-2).

Holds the reporter accounts and one local nonce per key, so several reports from the
same key can be pending at once. Keys are never printed or logged by this module, but
they are NOT isolated: the raw values stay in the process environment (REPORTER_KEYS)
and in memory for the life of the process.
"""
from __future__ import annotations

from web3 import Web3
from web3.exceptions import TransactionNotFound

MIN_BALANCE_WEI = 10 * 10**18  # CLAUDE.md hard rule: keep every EOA above 10 MON
PRIORITY_FEE_WEI = 2 * 10**9
# Spending caps (review M-2). Monad charges gas LIMIT x price, so a wrong estimate or a
# fee spike is paid in full. A send above either cap is refused (raised, never clamped)
# and retried on later ticks like any failed send.
GAS_CAP = 300_000                 # report_uptime: ~124k estimate x 1.2 = ~149k on py-evm (pinned in tests)
MAX_BASE_FEE_WEI = 1000 * 10**9   # Monad's minimum base fee is 100 gwei
FEE_BUMP = (5, 4)                 # x1.25 per replacement of a stuck tx (review M-3)


class SendRefused(Exception):
    """A cap above was exceeded; the message has numbers only and is safe to log."""


class Chain:
    def __init__(self, w3: Web3, address: str, abi: list, accounts: list,
                 priority_fee_wei: int = PRIORITY_FEE_WEI):
        """`accounts`: eth_account LocalAccount objects, in REPORTER_KEYS order (R-2)."""
        if not accounts:
            raise ValueError("no reporter keys")
        self.w3 = w3
        self.contract = w3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)
        self.accounts = list(accounts)
        self.nonces: dict[str, int | None] = {}  # address -> next nonce; None = resync
        self.priority_fee_wei = priority_fee_wei
        self.chain_id = w3.eth.chain_id
        self.grace = self.contract.functions.REPORT_GRACE().call()

    # ---- reads
    def now(self) -> int:
        """Chain time: timestamp of the latest block. The only clock the service uses."""
        return self.w3.eth.get_block("latest")["timestamp"]

    def block_number(self) -> int:
        return self.w3.eth.block_number

    def rental_created(self, from_block: int, to_block: int) -> list[dict]:
        """Args of every RentalCreated log in [from_block, to_block], oldest first."""
        logs = self.contract.events.RentalCreated().get_logs(from_block=from_block, to_block=to_block)
        return [dict(log["args"]) for log in logs]

    def get_slots(self, rental_id: int) -> list[int]:
        return self.contract.functions.get_slots(rental_id).call()

    def receipt_status(self, tx_hash: str) -> int | None:
        """1 success, 0 reverted, None not mined yet."""
        try:
            return self.w3.eth.get_transaction_receipt(tx_hash)["status"]
        except TransactionNotFound:
            return None

    def nonce_mined(self, address: str, nonce: int) -> bool:
        """True once some tx with this nonce is in a block: no other tx with it can land."""
        return self.w3.eth.get_transaction_count(address, "latest") > nonce

    def warn_low_balances(self) -> None:
        for acct in self.accounts:
            bal = self.w3.eth.get_balance(acct.address)
            if bal < MIN_BALANCE_WEI:
                print(f"WARNING reporter={acct.address} balance={bal / 10**18:.4f} MON "
                      f"is below 10 MON - fund it before the demo", flush=True)

    # ---- writes
    def account_for(self, rental_id: int):
        """R-2: key = keys[rental_id % len(keys)]."""
        return self.accounts[rental_id % len(self.accounts)]

    def send_report(self, rental_id: int, slot: int, up: bool,
                    replace: tuple[int, int, int] | None = None) -> tuple[str, int, int, int]:
        """Sign and broadcast report_uptime without waiting for it.

        Returns (tx hash, nonce, max fee, priority fee). Pass the last three back as
        `replace` to re-send a stuck report at the SAME nonce with both fees bumped, so
        at most one of the two can ever be mined (review M-3).
        Raises on a revert at estimation (e.g. "already reported"), on SendRefused, or
        on a failed send.
        """
        acct = self.account_for(rental_id)
        fn = self.contract.functions.report_uptime(rental_id, slot, up)
        # Monad charges the gas LIMIT, not gas used: estimate + 20 %, never a node default.
        gas = fn.estimate_gas({"from": acct.address}) * 12 // 10
        if gas > GAS_CAP:
            raise SendRefused(f"gas limit {gas} exceeds GAS_CAP {GAS_CAP}")
        base_fee = self.w3.eth.get_block("latest")["baseFeePerGas"]
        if base_fee > MAX_BASE_FEE_WEI:
            raise SendRefused(f"base fee {base_fee} exceeds MAX_BASE_FEE_WEI {MAX_BASE_FEE_WEI}")
        num, den = FEE_BUMP
        try:
            if replace:
                nonce = replace[0]
                priority = replace[2] * num // den + 1
                max_fee = max(2 * base_fee + priority, replace[1] * num // den + 1)
            else:
                nonce = self.nonces.get(acct.address)
                if nonce is None:
                    nonce = self.w3.eth.get_transaction_count(acct.address, "pending")
                priority = self.priority_fee_wei
                max_fee = 2 * base_fee + priority
            tx = fn.build_transaction({
                "from": acct.address,
                "nonce": nonce,
                "gas": gas,
                "maxFeePerGas": max_fee,
                "maxPriorityFeePerGas": priority,
                "chainId": self.chain_id,
            })
            tx_hash = self.w3.eth.send_raw_transaction(acct.sign_transaction(tx).raw_transaction)
        except Exception:
            if not replace:  # a replacement never moved the tracker
                self.nonces[acct.address] = None  # resync from the chain on the next send
            raise
        if not replace:
            self.nonces[acct.address] = nonce + 1
        return Web3.to_hex(tx_hash), nonce, max_fee, priority
