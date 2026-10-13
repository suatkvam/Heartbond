"""Shared fixtures: the real compiled contract on web3's in-process EthereumTesterProvider.

Time is moved with time travel; nothing sleeps. Reporter keys are generated here.
"""
import asyncio
import json
import subprocess
from pathlib import Path

import httpx
import pytest
from eth_account import Account
from web3 import EthereumTesterProvider, Web3

from oracle.chain import Chain
from oracle.service import Service

ROOT = Path(__file__).resolve().parents[2]
INTERVAL, N, GRACE = 30, 4, 30
UP, DOWN = 1, 2
URL_A, URL_B = "http://a.test", "http://b.test"


@pytest.fixture(scope="session")
def bytecode():
    out = subprocess.check_output(
        ["vyper", "-f", "abi,bytecode", str(ROOT / "contracts" / "GpuSlaEscrow.vy")], text=True)
    abi_line, code = out.strip().split("\n")
    # The service uses the checked-in ABI; it must describe the contract we deploy.
    assert json.loads(abi_line) == json.loads((ROOT / "shared/abi/GpuSlaEscrow.json").read_text())
    return code


class Env:
    def __init__(self, bytecode, balances=(20, 20)):
        self.w3 = Web3(EthereumTesterProvider())
        self.tester = self.w3.provider.ethereum_tester
        self.abi = json.loads((ROOT / "shared/abi/GpuSlaEscrow.json").read_text())
        self.funder, self.renter, self.prov_a, self.prov_b, self.stranger, self.outsider = self.w3.eth.accounts[:6]
        self.keys = [Account.create() for _ in balances]  # generated in-process, never real
        for acct, mon in zip(self.keys, balances):
            self.w3.eth.send_transaction({"from": self.funder, "to": acct.address, "value": mon * 10**18})
        tx = self.w3.eth.contract(abi=self.abi, bytecode=bytecode).constructor(
            [a.address for a in self.keys]).transact({"from": self.funder})
        rcpt = self.w3.eth.get_transaction_receipt(tx)
        self.deploy_block = rcpt["blockNumber"]
        self.chain = Chain(self.w3, rcpt["contractAddress"], self.abi, self.keys)
        self.c = self.chain.contract
        self.status = {"a.test": 200, "b.test": 200}  # host -> HTTP status of /health
        self.probes = []
        self.nodes = {self.prov_a.lower(): URL_A, self.prov_b.lower(): URL_B}
        self.renters = {self.renter.lower()}  # H-8 allow-list: the demo renter; `outsider` is not on it

    def handler(self, request):
        self.probes.append(request.url.host)
        return httpx.Response(self.status[request.url.host])

    def service(self, **kw):
        http = httpx.AsyncClient(transport=httpx.MockTransport(self.handler))
        return Service(self.chain, self.nodes, self.renters, http, self.deploy_block, **kw)

    def create(self, provider, start, renter=None):
        self.c.functions.create_rental(provider, 75, INTERVAL, start, start + N * INTERVAL, b"\0" * 32).transact(
            {"from": renter or self.renter, "value": 10**16})
        return self.c.functions.next_rental_id().call() - 1

    def warp(self, ts):
        """Make the latest block's timestamp exactly `ts`."""
        self.tester.time_travel(ts)
        self.tester.mine_blocks(1)
        assert self.chain.now() == ts

    def tick(self, svc, ts=None):
        if ts is not None:
            self.warp(ts)
        asyncio.run(svc.tick(self.chain.now()))

    def run(self, svc, start, until):
        """Tick every 5 chain seconds from `start` to `until` inclusive."""
        for ts in range(start, until + 1, 5):
            self.tick(svc, ts)

    def slots(self, rid):
        return self.c.functions.get_slots(rid).call()

    def nonce(self, i):
        return self.w3.eth.get_transaction_count(self.keys[i].address)

    def reported(self):
        return [dict(e["args"]) for e in self.c.events.UptimeReported().get_logs(from_block=0)]


@pytest.fixture
def env(bytecode):
    return Env(bytecode)
