"""Control API (SPEC H-5, H-6): the contract in docs/UI_HANDOFF.md section 7.

No authentication: the server is bound to 127.0.0.1 and is a demo panel only.
Do not expose it beyond localhost - anyone who reaches it can force slots Down.
The chain stays the source of truth; this API only shows oracle-side state.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, StrictInt
from starlette.middleware.trustedhost import TrustedHostMiddleware
from web3 import Web3

from oracle.service import Service, SlotReport
from oracle.slots import Rental

PORT = 8787
BALANCE_TTL_S = 30  # /health is polled by the UI; the public RPC is rate-limited


class ForceDown(BaseModel):
    slots: list[StrictInt] = Field(max_length=256)  # StrictInt: no "2", 2.0 or true


def create_app(service: Service) -> FastAPI:
    app = FastAPI(title="GPU SLA Escrow oracle")
    app.add_middleware(CORSMiddleware, allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
                       allow_methods=["*"], allow_headers=["*"])
    # DNS rebinding (review M-1): a hostile page whose name resolves to 127.0.0.1 is
    # same-origin with this API, so CORS does not stop it - but its Host header still
    # carries its own name. Added last = outermost; the port is ignored in the match.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    st, chain = service.state, service.chain
    balances: dict = {"at": float("-inf"), "ok": False, "wei": []}

    def rental(rental_id: int) -> Rental:
        r = st.rentals.get(rental_id)
        if r is None:
            raise HTTPException(404, f"rental {rental_id} is not tracked")
        return r

    def slots(r: Rental) -> list[dict]:
        out = []
        for k in range(r.n_slots):
            ok, total = r.probes.get(k, (0, 0))
            rep = st.reports.get((r.rental_id, k)) or SlotReport()
            out.append({
                "slot": k, "probesOk": ok, "probesTotal": total,
                "forcedDown": k in r.forced_down,
                # True from the moment a report tx is out (or the slot is on-chain):
                # from then on force-down no longer changes what the chain gets.
                "reported": rep.done or rep.tx is not None,
                # What was sent / is on-chain; before that, the verdict if sent now.
                "up": rep.up if rep.up is not None else r.verdict(k),
                "txHash": rep.tx,
            })
        return out

    # Sync handler: FastAPI runs it in its thread pool, so the balance RPC calls
    # never block the event loop the service ticks on.
    @app.get("/health")
    def health():
        if time.monotonic() - balances["at"] > BALANCE_TTL_S:
            try:
                wei, ok = [chain.w3.eth.get_balance(a.address) for a in chain.accounts], True
            except Exception as exc:
                print(f"health-error {type(exc).__name__} - balance read failed", flush=True)
                wei, ok = [None] * len(chain.accounts), False
            balances.update(at=time.monotonic(), ok=ok, wei=wei)
        return {
            "ok": balances["ok"],  # the RPC answered the last balance read
            "chainId": chain.chain_id,
            "contract": chain.contract.address,
            "reporters": [{"address": a.address, "balanceMon": None if w is None else w / 10**18}
                          for a, w in zip(chain.accounts, balances["wei"])],
        }

    @app.get("/nodes")
    async def nodes():
        out = []
        for provider, url in service.nodes.items():
            last = st.last_probe.get(provider)
            out.append({
                "provider": Web3.to_checksum_address(provider), "url": url,
                "lastProbe": last and {
                    "ok": last[0],
                    "at": datetime.fromtimestamp(last[1], timezone.utc).isoformat(),  # chain time
                    "latencyMs": round(last[2], 1),
                },
            })
        return out

    @app.get("/rentals")
    async def rentals():
        return [{"rentalId": r.rental_id, "provider": r.provider, "slots": slots(r)}
                for r in list(st.rentals.values())]

    @app.get("/rentals/{rental_id}")
    async def rental_detail(rental_id: int):
        r = rental(rental_id)
        return {"rentalId": r.rental_id, "slots": slots(r)}

    @app.post("/rentals/{rental_id}/force-down")
    async def force_down(rental_id: int, body: ForceDown):
        r = rental(rental_id)
        bad = [k for k in body.slots if not 0 <= k < r.n_slots]
        if bad:
            raise HTTPException(422, f"slots out of range 0..{r.n_slots - 1}: {bad}")
        r.force_down(body.slots)  # H-5; no effect on slots whose report is already out
        print(f"force-down rental={rental_id} slots={sorted(set(body.slots))}", flush=True)
        return {"ok": True}

    @app.delete("/rentals/{rental_id}/force-down")
    async def clear_force_down(rental_id: int):
        rental(rental_id).clear_force_down()
        print(f"force-down-cleared rental={rental_id}", flush=True)
        return {"ok": True}

    return app
