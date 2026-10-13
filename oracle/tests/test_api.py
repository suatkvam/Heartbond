"""T-010 (SPEC H-5, H-6): control API, checked against docs/UI_HANDOFF.md section 7.

Key sets below are copied from that table; a failure here means the API and the
handoff document disagree.
"""
import asyncio
import threading
from datetime import datetime

import httpx
import pytest
from fastapi.testclient import TestClient

from oracle.api import create_app
from oracle.tests.conftest import DOWN, INTERVAL, N, UP, URL_A

SLOT_KEYS = {"slot", "probesOk", "probesTotal", "forcedDown", "reported", "up", "txHash"}
LOCAL = "http://localhost:5173"
BASE = "http://127.0.0.1:8787"  # the API only answers to a local Host header (M-1)


@pytest.fixture
def api(env):
    """Service with one tracked rental of prov_a, one finished + reported slot."""
    env.start = env.chain.now() + 50
    env.rid = env.create(env.prov_a, env.start)
    env.svc = env.service()
    env.run(env.svc, env.start, env.start + INTERVAL)  # slot 0 completes and is sent
    env.client = TestClient(create_app(env.svc), base_url=BASE)
    return env


# ---------------------------------------------------------------- shapes

def test_get_health_shape(api):
    body = api.client.get("/health").json()
    assert set(body) == {"ok", "chainId", "contract", "reporters"}
    assert body["ok"] is True and body["chainId"] == api.chain.chain_id
    assert body["contract"] == api.c.address
    assert [set(r) for r in body["reporters"]] == [{"address", "balanceMon"}] * 2
    assert [r["address"] for r in body["reporters"]] == [k.address for k in api.keys]
    assert all(19 < r["balanceMon"] <= 20 for r in body["reporters"])


def test_get_health_reports_not_ok_when_rpc_fails_and_caches_balances(api, monkeypatch):
    calls = []

    def boom(addr):
        calls.append(addr)
        raise ConnectionError("rpc down")

    monkeypatch.setattr(api.chain.w3.eth, "get_balance", boom)
    for _ in range(3):
        body = api.client.get("/health").json()
    assert body["ok"] is False and body["reporters"][0]["balanceMon"] is None
    assert len(calls) == 1  # cached: polling /health does not hammer the RPC


def test_get_nodes_shape(api):
    body = api.client.get("/nodes").json()
    assert [set(n) for n in body] == [{"provider", "url", "lastProbe"}] * 2
    a, b = body
    assert (a["provider"], a["url"]) == (api.prov_a, URL_A)
    assert set(a["lastProbe"]) == {"ok", "at", "latencyMs"}
    assert a["lastProbe"]["ok"] is True and a["lastProbe"]["latencyMs"] >= 0
    at = datetime.fromisoformat(a["lastProbe"]["at"])  # ISO-8601, chain time of the probe
    assert at.tzinfo is not None and at.timestamp() == api.start + INTERVAL
    assert b["provider"] == api.prov_b and b["lastProbe"] is None  # never probed


def test_get_rentals_shape(api):
    body = api.client.get("/rentals").json()
    assert len(body) == 1 and set(body[0]) == {"rentalId", "provider", "slots"}
    assert (body[0]["rentalId"], body[0]["provider"]) == (api.rid, api.prov_a)
    assert len(body[0]["slots"]) == N and all(set(s) == SLOT_KEYS for s in body[0]["slots"])


def test_get_rental_shape(api):
    body = api.client.get(f"/rentals/{api.rid}").json()
    assert set(body) == {"rentalId", "slots"} and body["rentalId"] == api.rid
    assert [s["slot"] for s in body["slots"]] == list(range(N))
    assert all(set(s) == SLOT_KEYS for s in body["slots"])
    s0, s1 = body["slots"][:2]
    assert s0 == {"slot": 0, "probesOk": 6, "probesTotal": 6, "forcedDown": False, "reported": True,
                  "up": True, "txHash": api.svc.state.reports[(api.rid, 0)].tx}
    assert len(s0["txHash"]) == 66
    assert (s1["reported"], s1["txHash"], s1["forcedDown"]) == (False, None, False)  # null until sent


def test_post_and_delete_force_down_shape(api):
    r = api.client.post(f"/rentals/{api.rid}/force-down", json={"slots": [2, 3]})
    assert (r.status_code, r.json()) == (200, {"ok": True})
    r = api.client.delete(f"/rentals/{api.rid}/force-down")
    assert (r.status_code, r.json()) == (200, {"ok": True})


# ---------------------------------------------------------------- errors

def test_unknown_rental_id_is_404(api):
    assert api.client.get("/rentals/999").status_code == 404
    assert api.client.post("/rentals/999/force-down", json={"slots": [0]}).status_code == 404
    assert api.client.delete("/rentals/999/force-down").status_code == 404


@pytest.mark.parametrize("body", [
    {}, {"slots": 2}, {"slots": "2,3"}, {"slots": ["2"]}, {"slots": [1.5]}, {"slots": [True]},
    {"slots": [None]}, {"slots": [-1]}, {"slots": [N]}, {"slots": [1, N]}, [2, 3],
])
def test_force_down_rejects_bad_slots(api, body):
    r = api.client.post(f"/rentals/{api.rid}/force-down", json=body)
    assert r.status_code == 422
    assert not api.svc.state.rentals[api.rid].forced_down  # nothing applied, not even the valid 1


def test_non_integer_rental_id_is_422(api):
    assert api.client.get("/rentals/abc").status_code == 422


# ---------------------------------------------------------------- H-5 behaviour

def test_force_down_makes_verdict_down_and_delete_restores_it(api):
    env = api
    env.run(env.svc, env.start + INTERVAL + 5, env.start + 3 * INTERVAL - 5)  # healthy probes in slots 1, 2
    rental = env.svc.state.rentals[env.rid]
    assert rental.verdict(1) and rental.verdict(2)

    env.client.post(f"/rentals/{env.rid}/force-down", json={"slots": [2, 3]})
    assert rental.verdict(1) and not rental.verdict(2) and not rental.verdict(3)
    slots = env.client.get(f"/rentals/{env.rid}").json()["slots"]
    assert [s["forcedDown"] for s in slots] == [False, False, True, True]
    assert slots[2]["up"] is False and slots[2]["probesOk"] == slots[2]["probesTotal"] > 0

    env.client.delete(f"/rentals/{env.rid}/force-down")
    assert rental.verdict(2) and not rental.forced_down
    assert env.client.get(f"/rentals/{env.rid}").json()["slots"][2]["up"] is True


def test_force_down_through_api_before_report_lands_down_on_chain(api):
    env = api
    env.run(env.svc, env.start + INTERVAL + 5, env.start + 2 * INTERVAL - 5)  # slot 1: all probes ok
    assert env.client.post(f"/rentals/{env.rid}/force-down", json={"slots": [1]}).json() == {"ok": True}
    env.tick(env.svc, env.start + 2 * INTERVAL)  # slot 1 completes -> report goes out

    assert env.slots(env.rid)[:2] == [UP, DOWN]
    s1 = env.client.get(f"/rentals/{env.rid}").json()["slots"][1]
    assert (s1["reported"], s1["up"], s1["forcedDown"]) == (True, False, True)
    assert len(s1["txHash"]) == 66 and s1["probesOk"] == s1["probesTotal"] == 6


def test_force_down_on_reported_slot_is_accepted_but_changes_nothing_on_chain(api):
    env = api
    r = env.client.post(f"/rentals/{env.rid}/force-down", json={"slots": [0]})
    assert (r.status_code, r.json()) == (200, {"ok": True})
    env.run(env.svc, env.start + INTERVAL + 5, env.start + 2 * INTERVAL)

    assert env.slots(env.rid)[0] == UP and len(env.reported()) == 2  # no second report for slot 0
    s0 = env.client.get(f"/rentals/{env.rid}").json()["slots"][0]
    assert (s0["forcedDown"], s0["reported"], s0["up"]) == (True, True, True)  # the truth: reported Up


# ---------------------------------------------------------------- CORS

@pytest.mark.parametrize("origin", [LOCAL, "http://127.0.0.1:3000", "http://localhost"])
def test_cors_header_present_for_localhost_origin(api, origin):
    r = api.client.get("/nodes", headers={"Origin": origin})
    assert r.headers["access-control-allow-origin"] == origin
    pre = api.client.options(f"/rentals/{api.rid}/force-down", headers={
        "Origin": origin, "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type"})
    assert pre.status_code == 200 and pre.headers["access-control-allow-origin"] == origin


@pytest.mark.parametrize("origin", ["https://evil.example", "http://localhost.evil.example",
                                    "http://evil.example/?http://localhost:1"])
def test_cors_header_absent_for_foreign_origin(api, origin):
    r = api.client.get("/nodes", headers={"Origin": origin})
    assert "access-control-allow-origin" not in r.headers
    pre = api.client.options(f"/rentals/{api.rid}/force-down", headers={
        "Origin": origin, "Access-Control-Request-Method": "POST"})
    assert pre.status_code == 400 and "access-control-allow-origin" not in pre.headers


# ---------------------------------------------------------------- responsiveness

def test_api_answers_while_a_tick_is_blocked_in_an_rpc_call(api, monkeypatch):
    """The blocking web3 part of a tick runs off the event loop the API is served on."""
    env = api
    entered, release = threading.Event(), threading.Event()
    real = env.chain.block_number

    def slow_block_number():
        entered.set()
        assert release.wait(10)
        return real()

    monkeypatch.setattr(env.chain, "block_number", slow_block_number)

    async def scenario():
        transport = httpx.ASGITransport(app=create_app(env.svc))
        async with httpx.AsyncClient(transport=transport, base_url=BASE) as client:
            tick = asyncio.create_task(env.svc.tick(env.chain.now()))
            await asyncio.to_thread(entered.wait, 10)
            assert entered.is_set() and not tick.done()  # the tick is stuck inside "the RPC"
            resp = await asyncio.wait_for(client.get(f"/rentals/{env.rid}"), 2)
            post = await asyncio.wait_for(
                client.post(f"/rentals/{env.rid}/force-down", json={"slots": [3]}), 2)
            assert not tick.done()
            release.set()
            await tick
            return resp, post

    resp, post = asyncio.run(scenario())
    assert resp.status_code == 200 and post.json() == {"ok": True}
    assert env.svc.state.rentals[env.rid].forced_down == {3}


# ---------------------------------------------------------------- security review fixes

def test_m1_foreign_host_header_is_rejected_on_get_and_post(api):
    """DNS rebinding: the attacker's name resolves to 127.0.0.1 but is still in Host."""
    evil = {"Host": "evil.example:8787"}
    assert api.client.get("/rentals", headers=evil).status_code == 400
    r = api.client.post(f"/rentals/{api.rid}/force-down", json={"slots": [2]}, headers=evil)
    assert r.status_code == 400
    assert api.client.delete(f"/rentals/{api.rid}/force-down", headers=evil).status_code == 400
    assert not api.svc.state.rentals[api.rid].forced_down
    for host in ("127.0.0.1:8787", "localhost:8787", "localhost", "127.0.0.1:9999"):
        assert api.client.get("/rentals", headers={"Host": host}).status_code == 200
    for host in ("127.0.0.1.evil.example", "localhost.evil.example:8787", "evil.example"):
        assert api.client.get("/rentals", headers={"Host": host}).status_code == 400


def test_l8_force_down_slots_list_is_bounded(api):
    r = api.client.post(f"/rentals/{api.rid}/force-down", json={"slots": [0] * 257})
    assert r.status_code == 422 and not api.svc.state.rentals[api.rid].forced_down
    assert api.client.post(f"/rentals/{api.rid}/force-down", json={"slots": [0] * 256}).status_code == 200


@pytest.mark.parametrize("content_type", ["text/plain", "application/x-www-form-urlencoded",
                                          "multipart/form-data", None])
def test_l1_force_down_without_json_content_type_is_rejected(api, content_type):
    """A cross-site page can POST these without a CORS preflight; JSON it cannot."""
    req = api.client.build_request("POST", f"/rentals/{api.rid}/force-down", content=b'{"slots":[1]}')
    req.headers.pop("content-type", None)
    if content_type:
        req.headers["content-type"] = content_type
    r = api.client.send(req)
    assert 400 <= r.status_code < 500
    assert not api.svc.state.rentals[api.rid].forced_down


def test_l3_health_error_log_has_no_rpc_error_text(api, monkeypatch, capsys):
    def boom(addr):
        raise ConnectionError("https://rpc.example/v1/SECRET-API-TOKEN refused")

    monkeypatch.setattr(api.chain.w3.eth, "get_balance", boom)
    assert api.client.get("/health").json()["ok"] is False
    out = capsys.readouterr().out
    assert "health-error ConnectionError" in out and "SECRET" not in out
