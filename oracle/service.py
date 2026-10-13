"""Oracle service core: discovery, probe loop, report submission (SPEC H-1, H-3, H-4, H-7),
the two serving gates (H-8) and the per-rental report budget (H-9).

One step function, `Service.tick(now)`, where `now` is CHAIN time (latest block
timestamp). The local clock is used only to pace the loop in `run()`.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

import httpx

from oracle.chain import Chain, SendRefused
from oracle.config import node_url
from oracle.probe import probe
from oracle.slots import Rental

PROBE_INTERVAL_S = 5       # H-3
LOG_CHUNK = 1000           # H-1: blocks per eth_getLogs call
MAX_CHUNKS_PER_TICK = 10   # H-1: at most 10 getLogs per 5 s tick while catching up
PENDING_TIMEOUT_S = 20     # chain seconds without a receipt before a tx is replaced (same nonce)


@dataclass
class SlotReport:
    up: bool | None = None   # verdict carried by the last sent tx (or read from chain)
    tx: str | None = None    # hash of the last sent tx
    sent_at: int = 0         # chain time of that send
    nonce: int | None = None # nonce of that tx; a re-send of a stuck tx reuses it (review M-3)
    fees: tuple[int, int] = (0, 0)  # (max fee, priority fee) of that tx, bumped on a re-send
    done: bool = False       # slot is non-empty on-chain
    gave_up: bool = False    # reporting window closed, or budget spent, before a report landed
    sends: int = 0           # broadcasts made for this slot (H-9); in memory, reset by a restart


@dataclass
class State:
    """Everything the control API (T-010) needs to read."""
    last_block: int                                                    # last block scanned for logs
    rentals: dict[int, Rental] = field(default_factory=dict)
    reports: dict[tuple[int, int], SlotReport] = field(default_factory=dict)  # (rental_id, slot)
    last_probe: dict[str, tuple[bool, int, float]] = field(default_factory=dict)  # provider -> (ok, chain ts, ms)
    budget_spent: set[int] = field(default_factory=set)                # rental ids whose H-9 line was logged


class Service:
    def __init__(self, chain: Chain, nodes: dict[str, str], renters: set[str],
                 http: httpx.AsyncClient, deploy_block: int, log_chunk: int = LOG_CHUNK):
        """`nodes` and `renters` as returned by oracle.config (lower-cased addresses)."""
        self.chain, self.nodes, self.renters = chain, nodes, renters
        self.http, self.log_chunk = http, log_chunk
        self.state = State(last_block=deploy_block - 1)
        if not renters:  # H-8 fails closed
            print("WARNING renter allow-list is empty - no rental will be served "
                  "(set [renters] allow in the oracle config)", flush=True)

    async def tick(self, now: int) -> None:
        # web3 calls are synchronous: discover/report run in a worker thread so the
        # control API (same event loop) keeps answering during RPC round trips.
        # ponytail: no lock. One worker at a time (awaited in sequence); the API only
        # does GIL-atomic reads/writes on State (list() snapshots, .get, set updates).
        # Add a threading.Lock if State ever needs multi-step consistency.
        try:
            await asyncio.to_thread(self.discover)
        except Exception as exc:  # RPC hiccup: keep probing, rescan the same range next tick
            print(f"discover-error {type(exc).__name__} - rescan next tick", flush=True)
        await self.probe_all(now)
        await asyncio.to_thread(self.report, now)

    def discover(self) -> None:
        """H-1: scan RentalCreated logs in bounded chunks, remembering the last block."""
        # ponytail: no reorg handling; a rental created in a reorged-out block stays tracked.
        st = self.state
        head = self.chain.block_number()
        for _ in range(MAX_CHUNKS_PER_TICK):
            if st.last_block >= head:
                break
            lo = st.last_block + 1
            hi = min(lo + self.log_chunk - 1, head)
            for a in self.chain.rental_created(lo, hi):
                rid = a["rental_id"]
                # H-8: both gates, decided from the event alone, before any other call.
                if node_url(self.nodes, a["provider"]) is None:
                    print(f"ignore rental={rid} provider={a['provider']} reason=no-node-in-config", flush=True)
                    continue
                if a["renter"].lower() not in self.renters:
                    print(f"ignore rental={rid} renter={a['renter']} reason=renter-not-allowed", flush=True)
                    continue
                if rid in st.rentals:
                    continue  # rescanned chunk: keep the probe counts and force-down marks
                st.rentals[rid] = Rental(rid, a["provider"], a["start"], a["end"], a["interval"])
                # Slots already on-chain (service restart, other reporter) need no tx.
                for k, v in enumerate(self.chain.get_slots(rid)):
                    if v:
                        st.reports[(rid, k)] = SlotReport(up=v == 1, done=True)
                print(f"track rental={rid} provider={a['provider']} start={a['start']} end={a['end']} "
                      f"interval={a['interval']} reporter={self.chain.account_for(rid).address}", flush=True)
            st.last_block = hi

    async def probe_all(self, now: int) -> None:
        """H-3: one probe per provider with a running rental, attributed to chain time `now`."""
        running = [r for r in self.state.rentals.values() if r.start <= now < r.end]
        providers = sorted({r.provider.lower() for r in running})
        results = await asyncio.gather(*(probe(self.http, self.nodes[p], p) for p in providers))
        for p, (ok, ms) in zip(providers, results):
            self.state.last_probe[p] = (ok, now, ms)
        for r in running:
            r.record(now, self.state.last_probe[r.provider.lower()][0])

    def report(self, now: int) -> None:
        """H-4: report every slot completed by chain time; retry until end + REPORT_GRACE
        or until the H-9 budget is spent, whichever comes first."""
        for r in self.state.rentals.values():
            for k in range(r.n_slots):
                if now < r.start + (k + 1) * r.interval:
                    break  # O-5: this slot and all later ones are unfinished
                rep = self.state.reports.setdefault((r.rental_id, k), SlotReport())
                if rep.done or rep.gave_up:
                    continue
                tag = f"rental={r.rental_id} slot={k}"
                if rep.tx:
                    status = self.chain.receipt_status(rep.tx)
                    if status == 1:
                        rep.done = True
                        print(f"confirmed hash={rep.tx} {tag} up={rep.up}", flush=True)
                        continue
                    if status is None and now - rep.sent_at < PENDING_TIMEOUT_S:
                        continue  # still pending
                    print(f"tx-failed hash={rep.tx} {tag} status={status}", flush=True)
                    reporter = self.chain.account_for(r.rental_id).address
                    if status == 0 or self.chain.nonce_mined(reporter, rep.nonce):
                        # That nonce is spent, so no tx sent for this slot can still be
                        # mined: a fresh nonce is safe. (If it was our own report that
                        # landed, the estimate in send() reverts "already reported".)
                        rep.tx = rep.nonce = None
                    # else: pending or dropped. send() replaces it at the SAME nonce with
                    # a higher fee, so at most one tx per slot is ever mined (review M-3).
                if now > r.end + self.chain.grace:  # O-3: reporting closed
                    rep.gave_up = True
                    print(f"give-up {tag} reason=reporting-closed", flush=True)
                    continue
                self.send(r, k, rep, now)

    def send(self, r: Rental, k: int, rep: SlotReport, now: int) -> None:
        # Verdict is decided at the first send (force-down counts until a tx is out);
        # a replacement carries the same verdict as the tx it replaces.
        replace = (rep.nonce, *rep.fees) if rep.tx else None
        up = rep.up if replace else r.verdict(k)
        reporter = self.chain.account_for(r.rental_id).address
        tag = f"rental={r.rental_id} slot={k}"
        # H-9 budget (D-11): at most 2 * n_slots broadcasts per rental. The first broadcast
        # of each slot is always allowed (at most n_slots of those); every later broadcast
        # of a slot - a re-send after a failed tx or a same-nonce fee replacement - comes
        # out of one pool of n_slots shared by the rental. So a slot never broadcast is
        # never blocked by other slots' retries. A send that raises is not counted.
        if rep.sends:
            sends = [s.sends for j in range(r.n_slots) if (s := self.state.reports.get((r.rental_id, j)))]
            if sum(sends) - sum(map(bool, sends)) >= r.n_slots:
                rep.gave_up = True
                if r.rental_id not in self.state.budget_spent:
                    self.state.budget_spent.add(r.rental_id)
                    print(f"budget-spent rental={r.rental_id} used={sum(sends)}/{2 * r.n_slots} "
                          f"- no more re-submissions for this rental", flush=True)
                return
        try:
            tx, nonce, *fees = self.chain.send_report(r.rental_id, k, up, replace)
        except Exception as exc:
            try:
                onchain = self.chain.get_slots(r.rental_id)[k]
            except Exception:
                onchain = 0
            if onchain or "already reported" in str(exc):
                rep.done = True
                rep.up = onchain == 1 if onchain else rep.up
                print(f"already-reported {tag} up={rep.up}", flush=True)
            else:
                # Raw RPC error text is not logged (review L-3); our own refusals are.
                why = f"SendRefused: {exc}" if isinstance(exc, SendRefused) else type(exc).__name__
                print(f"report-error {tag} reporter={reporter} {why} - will retry", flush=True)
            return
        rep.up, rep.tx, rep.sent_at, rep.nonce, rep.fees = up, tx, now, nonce, tuple(fees)
        rep.sends += 1
        print(f"tx hash={tx} {tag} up={up} reporter={reporter}"
              f"{f' replaces-nonce={nonce}' if replace else ''}", flush=True)  # H-7

    async def run(self) -> None:
        while True:
            t0 = time.monotonic()
            try:
                await self.tick(await asyncio.to_thread(self.chain.now))
            except Exception as exc:
                print(f"tick-error {type(exc).__name__} - next tick in {PROBE_INTERVAL_S} s", flush=True)
            await asyncio.sleep(max(0.0, PROBE_INTERVAL_S - (time.monotonic() - t0)))
