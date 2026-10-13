"""T-013: full local end-to-end runs (SPEC section 5 demo parameters, PRD section 20).

Real compiled contract on the in-process eth-tester chain, the real `Service.tick`
loop, the real control API app, time travel instead of waiting, and a stub health
endpoint the test flips. interval 30, N = 4, threshold 75, price 0.01 MON,
start = now + 15. A third account (not renter, provider or reporter) calls `settle`
and `finalize`; the payee calls `withdraw`.
"""
import httpx
import pytest
from fastapi.testclient import TestClient

from oracle.api import create_app
from oracle.tests.conftest import DOWN, GRACE, INTERVAL, N, UP

PRICE = 10**16          # 0.01 MON, what Env.create escrows
WINDOW = 60             # CHALLENGE_WINDOW
RENTAL_FIELDS = ("renter", "provider", "price", "threshold", "interval", "start", "end", "n_slots",
                 "up_count", "reported_count", "status", "proposed_at", "compliant",
                 "renter_objected", "provider_objected", "spec_ref")
SETTLED = 3
HEALTHY = {k: [6, 6] for k in range(N)}  # one probe per 5 s tick, 6 per 30 s slot


@pytest.fixture
def env(env):
    """conftest's env, with a stub node that can also refuse connections (status None),
    which is what `docker stop` looks like to the probe."""
    def handler(request):
        host = request.url.host
        env.probes.append(host)
        if env.status[host] is None:
            raise httpx.ConnectError("connection refused", request=request)
        return httpx.Response(env.status[host])

    env.handler = handler
    assert env.c.functions.CHALLENGE_WINDOW().call() == WINDOW
    assert not env.c.functions.is_reporter(env.stranger).call()
    assert env.stranger not in (env.renter, env.prov_a, env.prov_b)
    return env


# ---------------------------------------------------------------- helpers

def begin(env, *providers):
    """Create one rental per provider, all with start = now + 15. Returns (start, ids)."""
    start = env.chain.now() + 15
    rids = [env.create(p, start) for p in providers]
    for rid in rids:
        r = rental(env, rid)
        assert (r["price"], r["threshold"], r["interval"], r["n_slots"], r["start"]) == (PRICE, 75, INTERVAL, N, start)
    return start, rids


def drive(env, svc, start, actions=None, skip=()):
    """Tick every 5 chain seconds from start - 10 to end + REPORT_GRACE.

    `actions`: offset from start -> callable run just before that tick.
    `skip`: offsets at which the service does not tick at all.
    """
    for off in range(-10, N * INTERVAL + GRACE + 1, 5):
        if actions and off in actions:
            actions[off]()
        if off not in skip:
            env.tick(svc, start + off)


def rental(env, rid):
    return dict(zip(RENTAL_FIELDS, env.c.functions.rentals(rid).call()))


def at_least(env, ts):
    if env.chain.now() < ts:
        env.warp(ts)


def call(env, fn, sender):
    rcpt = env.w3.eth.wait_for_transaction_receipt(fn.transact({"from": sender}))
    assert rcpt["status"] == 1
    return rcpt


def settle(env, rid):
    """The third account settles strictly after end + REPORT_GRACE. Returns the proposal."""
    at_least(env, rental(env, rid)["end"] + GRACE + 1)
    rcpt = call(env, env.c.functions.settle(rid), env.stranger)
    args = dict(env.c.events.SettlementProposed().process_receipt(rcpt)[0]["args"])
    assert args["caller"] == env.stranger
    return args


def finalize(env, rid):
    """The third account finalizes once the challenge window closed. Returns the event args."""
    at_least(env, rental(env, rid)["proposed_at"] + WINDOW)
    rcpt = call(env, env.c.functions.finalize(rid), env.stranger)
    args = dict(env.c.events.SettlementFinalized().process_receipt(rcpt)[0]["args"])
    assert args["caller"] == env.stranger and rental(env, rid)["status"] == SETTLED
    return args


def withdraw(env, who, expect):
    """`who` withdraws; its balance must grow by exactly `expect` minus the gas it paid.

    Also the check that the chain's fork runs the contract's transient-storage
    re-entrancy lock (`withdraw` is @nonreentrant): the tx must succeed, not revert.
    """
    assert env.c.functions.credits(who).call() == expect
    before = env.w3.eth.get_balance(who)
    rcpt = call(env, env.c.functions.withdraw(), who)
    assert dict(env.c.events.Withdrawn().process_receipt(rcpt)[0]["args"]) == {"account": who, "amount": expect}
    assert env.w3.eth.get_balance(who) == before + expect - rcpt["gasUsed"] * rcpt["effectiveGasPrice"]
    assert env.c.functions.credits(who).call() == 0


def pay_out(env, rid, payee, loser, compliant, up_count):
    """settle -> finalize -> withdraw, with the on-chain facts of each step asserted."""
    proposal = settle(env, rid)
    assert (proposal["up_count"], proposal["n_slots"], proposal["compliant"]) == (up_count, N, compliant)
    assert (proposal["payee"], proposal["amount"]) == (payee, PRICE)
    final = finalize(env, rid)
    assert (final["payee"], final["amount"]) == (payee, PRICE)
    assert env.c.functions.credits(loser).call() == 0
    withdraw(env, payee, PRICE)


def reporters(env, rid):
    return {e["reporter"] for e in env.reported() if e["rental_id"] == rid}


# ---------------------------------------------------------------- scenarios

def test_a_healthy_node_four_up_reports_provider_paid(env):
    start, (rid,) = begin(env, env.prov_a)
    svc = env.service()
    drive(env, svc, start)

    assert svc.state.rentals[rid].probes == HEALTHY
    assert env.slots(rid) == [UP] * N
    events = [e for e in env.reported() if e["rental_id"] == rid]
    assert [(e["slot"], e["up"]) for e in events] == [(k, True) for k in range(N)]
    assert reporters(env, rid) == {env.keys[rid % 2].address}  # R-2
    assert all(svc.state.reports[(rid, k)].done for k in range(N))
    r = rental(env, rid)
    assert (r["up_count"], r["reported_count"]) == (4, 4)

    pay_out(env, rid, payee=env.prov_a, loser=env.renter, compliant=True, up_count=4)
    assert env.w3.eth.get_balance(env.c.address) == 0


def test_b_node_down_for_two_slots_renter_refunded(env):
    start, (rid,) = begin(env, env.prov_a)
    svc = env.service()
    drive(env, svc, start, actions={2 * INTERVAL: lambda: env.status.update({"a.test": None})})

    assert svc.state.rentals[rid].probes == {0: [6, 6], 1: [6, 6], 2: [0, 6], 3: [0, 6]}
    assert env.slots(rid) == [UP, UP, DOWN, DOWN]
    r = rental(env, rid)
    assert (r["up_count"], r["reported_count"]) == (2, 4)

    pay_out(env, rid, payee=env.renter, loser=env.prov_a, compliant=False, up_count=2)
    assert env.w3.eth.get_balance(env.c.address) == 0


def test_c_force_down_two_slots_via_control_api_renter_refunded(env):
    start, (rid,) = begin(env, env.prov_a)
    svc = env.service()
    api = TestClient(create_app(svc), base_url="http://127.0.0.1:8787")

    def force():
        assert api.post(f"/rentals/{rid}/force-down", json={"slots": [2, 3]}).json() == {"ok": True}

    drive(env, svc, start, actions={INTERVAL + 10: force})  # mid slot 1, as on stage

    assert svc.state.rentals[rid].probes == HEALTHY  # the node never failed a probe
    assert env.slots(rid) == [UP, UP, DOWN, DOWN]
    detail = api.get(f"/rentals/{rid}").json()["slots"]
    assert [(s["forcedDown"], s["up"], s["reported"]) for s in detail] == \
        [(False, True, True)] * 2 + [(True, False, True)] * 2
    assert rental(env, rid)["up_count"] == 2

    pay_out(env, rid, payee=env.renter, loser=env.prov_a, compliant=False, up_count=2)


def test_d_slot_without_any_probe_is_reported_down_and_rental_still_passes(env):
    start, (rid,) = begin(env, env.prov_a)
    svc = env.service()
    drive(env, svc, start, skip=range(INTERVAL, 2 * INTERVAL))  # the service is absent for slot 1

    probes = svc.state.rentals[rid].probes
    assert 1 not in probes and probes == {0: [6, 6], 2: [6, 6], 3: [6, 6]}
    assert env.status["a.test"] == 200  # the node was healthy the whole time
    assert env.slots(rid) == [UP, DOWN, UP, UP]  # zero probes -> Down, never Up (H-3)
    assert {(e["slot"], e["up"]) for e in env.reported()} == {(0, True), (1, False), (2, True), (3, True)}
    assert rental(env, rid)["up_count"] == 3

    # 100 * 3 >= 75 * 4: the boundary still passes
    pay_out(env, rid, payee=env.prov_a, loser=env.renter, compliant=True, up_count=3)


def test_e_two_overlapping_rentals_two_nodes_two_reporter_keys(env):
    start, (r1, r2) = begin(env, env.prov_a, env.prov_b)
    assert r1 % 2 != r2 % 2
    svc = env.service()
    drive(env, svc, start, actions={2 * INTERVAL: lambda: env.status.update({"b.test": None})})

    assert env.slots(r1) == [UP] * N
    assert env.slots(r2) == [UP, UP, DOWN, DOWN]
    assert svc.state.rentals[r1].probes == HEALTHY  # node-b going down did not touch rental 1
    assert reporters(env, r1) == {env.keys[r1 % 2].address}
    assert reporters(env, r2) == {env.keys[r2 % 2].address}
    assert reporters(env, r1) != reporters(env, r2)
    assert len(env.reported()) == 2 * N

    p1, p2 = settle(env, r1), settle(env, r2)
    assert (p1["compliant"], p1["up_count"], p1["payee"]) == (True, 4, env.prov_a)
    assert (p2["compliant"], p2["up_count"], p2["payee"]) == (False, 2, env.renter)
    assert (finalize(env, r1)["payee"], finalize(env, r2)["payee"]) == (env.prov_a, env.renter)
    assert env.c.functions.credits(env.prov_b).call() == 0
    withdraw(env, env.prov_a, PRICE)
    withdraw(env, env.renter, PRICE)
    assert env.w3.eth.get_balance(env.c.address) == 0


@pytest.mark.parametrize("node_fails", [True, False], ids=["provider-loses", "renter-loses"])
def test_f_objection_by_losing_party_does_not_change_payout(env, node_fails):
    start, (rid,) = begin(env, env.prov_a)
    svc = env.service()
    actions = {2 * INTERVAL: lambda: env.status.update({"a.test": None})} if node_fails else None
    drive(env, svc, start, actions=actions)
    payee, loser = (env.renter, env.prov_a) if node_fails else (env.prov_a, env.renter)

    proposal = settle(env, rid)
    assert (proposal["payee"], proposal["amount"]) == (payee, PRICE)
    env.warp(proposal["proposed_at"] + WINDOW // 2)  # inside the challenge window
    rcpt = call(env, env.c.functions.raise_objection(rid), loser)
    objection = dict(env.c.events.ObjectionRaised().process_receipt(rcpt)[0]["args"])
    assert objection == {"rental_id": rid, "by": loser, "is_renter": loser == env.renter}
    r = rental(env, rid)
    assert (r["renter_objected"], r["provider_objected"]) == (loser == env.renter, loser == env.prov_a)
    assert r["compliant"] == proposal["compliant"]

    final = finalize(env, rid)
    assert (final["payee"], final["amount"]) == (proposal["payee"], proposal["amount"])
    assert env.c.functions.credits(loser).call() == 0
    withdraw(env, payee, PRICE)
