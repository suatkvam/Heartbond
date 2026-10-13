"""T-009 (SPEC H-1, H-3, H-4, H-7, R-2): discovery, probe/report loop, report submission.

Runs the real compiled contract on web3's in-process EthereumTesterProvider (py-evm),
so log filters, gas estimation, signing, raw sends and receipts go through web3.
Fixtures live in conftest.py.
"""
import asyncio
import json

import pytest
from eth_account import Account
from eth_account.typed_transactions import TypedTransaction

import oracle.__main__ as entry
from oracle import chain as chain_mod
from oracle import config, service
from oracle.tests.conftest import DOWN, GRACE, INTERVAL, N, ROOT, UP, Env


# ---------------------------------------------------------------- H-1 discovery

def test_discovery_reads_logs_in_bounded_chunks(env, monkeypatch):
    start = env.chain.now() + 500
    for provider in (env.prov_a, env.prov_b, env.prov_a):
        env.create(provider, start)
        env.tester.mine_blocks(7)
    ranges = []
    real = env.chain.rental_created
    monkeypatch.setattr(env.chain, "rental_created", lambda lo, hi: ranges.append((lo, hi)) or real(lo, hi))
    monkeypatch.setattr(service, "MAX_CHUNKS_PER_TICK", 3)
    svc = env.service(log_chunk=5)
    head = env.chain.block_number()

    env.tick(svc)
    assert len(ranges) == 3  # bounded work per tick
    assert svc.state.last_block == env.deploy_block + 14 and 3 not in svc.state.rentals
    while svc.state.last_block < head:
        env.tick(svc)

    assert set(svc.state.rentals) == {1, 2, 3}
    assert ranges[0][0] == env.deploy_block
    assert all(hi - lo + 1 <= 5 for lo, hi in ranges)
    assert all(b[0] == a[1] + 1 for a, b in zip(ranges, ranges[1:]))  # contiguous, no rescans
    assert len(ranges) > 3
    r = svc.state.rentals[2]
    assert (r.provider, r.start, r.end, r.interval) == (env.prov_b, start, start + N * INTERVAL, INTERVAL)

    seen = len(ranges)
    asyncio.run(svc.tick(env.chain.now()))  # no new block: nothing to scan
    assert len(ranges) == seen


def test_unknown_provider_rental_is_ignored_and_sends_no_tx(env, capsys):
    start = env.chain.now() + 50
    rid = env.create(env.stranger, start)
    svc = env.service()
    env.run(svc, start, start + N * INTERVAL + GRACE + 5)

    assert rid not in svc.state.rentals and not svc.state.reports
    assert env.probes == []
    assert env.slots(rid) == [0] * N
    assert env.nonce(0) == env.nonce(1) == 0
    out = capsys.readouterr().out
    assert out.count(f"ignore rental={rid} provider={env.stranger}") == 1
    assert "tx hash=" not in out


# ---------------------------------------------------------------- R-2 key selection

def test_two_rentals_are_reported_by_two_different_keys(env):
    start = env.chain.now() + 50
    r1, r2 = env.create(env.prov_a, start), env.create(env.prov_b, start)
    assert (r1 % 2, r2 % 2) == (1, 0)
    svc = env.service()
    env.run(svc, start, start + INTERVAL)

    by_rental = {e["rental_id"]: e["reporter"] for e in env.reported()}
    assert by_rental == {r1: env.keys[1].address, r2: env.keys[0].address}
    for rid in (r1, r2):  # the tx sender is that key too
        tx = env.w3.eth.get_transaction(svc.state.reports[(rid, 0)].tx)
        assert tx["from"] == env.keys[rid % 2].address
    assert env.nonce(0) == env.nonce(1) == 1


# ---------------------------------------------------------------- H-4 timing and gas

def test_no_report_before_slot_completes_by_chain_time_then_report(env, monkeypatch):
    start = env.chain.now() + 50
    rid = env.create(env.prov_a, start)
    svc = env.service()
    sends = []
    real = env.chain.send_report
    monkeypatch.setattr(env.chain, "send_report", lambda *a: sends.append(a) or real(*a))

    env.run(svc, start, start + 25)
    env.tick(svc, start + INTERVAL - 1)  # last second of slot 0
    assert sends == [] and env.slots(rid) == [0] * N and env.nonce(1) == 0

    env.tick(svc, start + INTERVAL)  # chain time reached the slot end
    assert sends == [(rid, 0, True, None)]  # None: a first send, not a replacement
    assert env.slots(rid) == [UP, 0, 0, 0]


def test_report_tx_has_explicit_gas_limit_of_estimate_times_1_2(env):
    start = env.chain.now() + 50
    rid = env.create(env.prov_a, start)
    svc = env.service()
    env.run(svc, start, start + 25)
    env.warp(start + INTERVAL)
    estimate = env.c.functions.report_uptime(rid, 0, True).estimate_gas({"from": env.keys[1].address})

    env.tick(svc)
    tx = env.w3.eth.get_transaction(svc.state.reports[(rid, 0)].tx)
    assert tx["gas"] == estimate * 12 // 10
    assert tx["gas"] < env.w3.eth.get_block("latest")["gasLimit"] // 100  # not a node/block default
    assert tx["maxPriorityFeePerGas"] == env.chain.priority_fee_wei  # explicit fee fields
    assert tx["maxFeePerGas"] > tx["maxPriorityFeePerGas"]
    receipt = env.w3.eth.get_transaction_receipt(tx["hash"])
    assert receipt["status"] == 1 and receipt["gasUsed"] <= tx["gas"]


# ---------------------------------------------------------------- H-4 retries

def test_failed_send_is_retried_on_a_later_tick(env, monkeypatch, capsys):
    start = env.chain.now() + 50
    rid = env.create(env.prov_a, start)
    svc = env.service()
    env.run(svc, start, start + 25)

    def boom(raw):
        raise ConnectionError("rpc down")

    with monkeypatch.context() as m:
        m.setattr(env.w3.eth, "send_raw_transaction", boom)
        env.tick(svc, start + INTERVAL)
    rep = svc.state.reports[(rid, 0)]
    assert rep.tx is None and not rep.done and env.slots(rid)[0] == 0
    assert f"report-error rental={rid} slot=0" in capsys.readouterr().out

    env.tick(svc, start + INTERVAL + 5)  # send works again
    assert rep.tx and env.slots(rid)[0] == UP
    env.tick(svc, start + INTERVAL + 10)  # receipt seen
    assert rep.done and env.nonce(1) == 1


def test_lost_tx_is_resent_after_pending_timeout(env, monkeypatch):
    start = env.chain.now() + 50
    rid = env.create(env.prov_a, start)
    svc = env.service()
    env.run(svc, start, start + 25)
    with monkeypatch.context() as m:  # node accepts the tx and drops it
        m.setattr(env.w3.eth, "send_raw_transaction", lambda raw: b"\x11" * 32)
        env.tick(svc, start + INTERVAL)
    rep = svc.state.reports[(rid, 0)]
    lost = rep.tx
    assert lost == "0x" + "11" * 32

    env.tick(svc, start + INTERVAL + 5)  # still inside the pending timeout: wait
    assert rep.tx == lost and env.slots(rid)[0] == 0
    # Timed out: the nonce (locally 1, on-chain 0) is resynced and the report re-sent.
    env.tick(svc, start + INTERVAL + service.PENDING_TIMEOUT_S)
    assert rep.tx != lost and env.slots(rid)[0] == UP
    assert env.w3.eth.get_transaction(rep.tx)["nonce"] == 0


def test_no_retry_after_end_plus_report_grace(env, monkeypatch, capsys):
    start = env.chain.now() + 50
    end = start + N * INTERVAL
    rid = env.create(env.prov_a, start)
    svc = env.service()
    attempts = []

    def boom(*a):
        attempts.append(a)
        raise ConnectionError("rpc down")

    monkeypatch.setattr(env.chain, "send_report", boom)
    env.run(svc, start, end + GRACE)
    assert len(attempts) > N  # retried on later ticks, up to and including end + GRACE
    before = len(attempts)

    env.run(svc, end + GRACE + 1, end + GRACE + 11)
    assert len(attempts) == before  # reporting closed: no further attempt
    assert all(svc.state.reports[(rid, k)].gave_up for k in range(N))
    assert env.slots(rid) == [0] * N and env.nonce(1) == 0
    assert capsys.readouterr().out.count("give-up rental=") == N  # logged once per slot


def test_already_reported_slot_is_treated_as_done(env, monkeypatch, capsys):
    start = env.chain.now() + 50
    rid = env.create(env.prov_a, start)
    svc = env.service()
    env.run(svc, start, start + 25)
    env.warp(start + INTERVAL)
    # Another allow-listed key reports slot 0 first (rental 1 belongs to keys[1]).
    other = env.keys[0]
    tx = env.c.functions.report_uptime(rid, 0, False).build_transaction(
        {"from": other.address, "nonce": 0, "gas": 200_000})
    env.w3.eth.send_raw_transaction(other.sign_transaction(tx).raw_transaction)

    env.tick(svc)
    rep = svc.state.reports[(rid, 0)]
    assert rep.done and rep.tx is None and rep.up is False  # verdict taken from the chain
    assert env.nonce(1) == 0  # our key sent nothing
    assert f"already-reported rental={rid} slot=0" in capsys.readouterr().out

    # A restarted service finds the slot non-empty at discovery and never tries to send.
    fresh = env.service()
    monkeypatch.setattr(env.chain, "send_report", lambda *a: pytest.fail("must not send"))
    env.tick(fresh)
    assert fresh.state.reports[(rid, 0)].done


# ---------------------------------------------------------------- H-3 verdicts on-chain

def test_slots_without_probes_are_backfilled_down(env):
    start = env.chain.now() + 50
    rid = env.create(env.prov_a, start)
    svc = env.service()
    env.tick(svc, start + 2 * INTERVAL + 5)  # service starts in slot 2; node is healthy

    assert env.slots(rid) == [DOWN, DOWN, 0, 0]
    assert [(e["slot"], e["up"]) for e in env.reported()] == [(0, False), (1, False)]
    assert env.nonce(1) == 2  # two reports from one key, sent in the same tick


def test_healthy_probes_report_up_and_failed_probe_reports_down(env):
    start = env.chain.now() + 50
    end = start + N * INTERVAL
    rid = env.create(env.prov_a, start)
    svc = env.service()
    env.run(svc, start, start + 2 * INTERVAL + 5)
    env.status["a.test"] = 503  # one failed probe inside slot 2
    env.tick(svc, start + 2 * INTERVAL + 10)
    env.status["a.test"] = 200
    env.run(svc, start + 2 * INTERVAL + 15, end + 5)

    assert env.slots(rid) == [UP, UP, DOWN, UP]
    assert env.c.functions.rentals(rid).call()[8] == 3  # up_count
    assert svc.state.rentals[rid].probes[2] == [5, 6]
    assert all(svc.state.reports[(rid, k)].done for k in range(N))


def test_all_healthy_gives_up_count_equal_to_slots(env):
    start = env.chain.now() + 50
    rid = env.create(env.prov_a, start)
    svc = env.service()
    env.run(svc, start, start + N * INTERVAL)
    assert env.slots(rid) == [UP] * N
    assert env.c.functions.rentals(rid).call()[8] == N


def test_force_down_before_send_reports_down(env):
    start = env.chain.now() + 50
    rid = env.create(env.prov_a, start)
    svc = env.service()
    env.run(svc, start, start + 25)
    svc.state.rentals[rid].force_down([0])
    env.tick(svc, start + INTERVAL)
    assert env.slots(rid)[0] == DOWN


# ---------------------------------------------------------------- H-7 logging, keys, startup

def test_tx_log_line_has_hash_and_no_private_key_is_logged(env, capsys):
    start = env.chain.now() + 50
    r1, r2 = env.create(env.prov_a, start), env.create(env.prov_b, start)
    svc = env.service()
    env.chain.warn_low_balances()
    env.run(svc, start, start + N * INTERVAL + GRACE + 5)
    captured = capsys.readouterr()
    text = captured.out + captured.err

    for rid in (r1, r2):
        tx = svc.state.reports[(rid, 0)].tx
        assert len(tx) == 66
        assert f"tx hash={tx} rental={rid} slot=0 up=True reporter={env.keys[rid % 2].address}" in captured.out
    assert captured.out.count("tx hash=0x") == 2 * N
    assert captured.out.count("probe provider=") == len(env.probes) > 0
    for acct in env.keys:
        assert acct.key.hex().removeprefix("0x").lower() not in text.lower()


def test_low_balance_warning_below_10_mon(bytecode, capsys):
    env = Env(bytecode, balances=(20, 9))
    env.chain.warn_low_balances()
    out = capsys.readouterr().out
    assert f"WARNING reporter={env.keys[1].address}" in out and "below 10 MON" in out
    assert env.keys[0].address not in out


def test_missing_deployment_address_is_a_clear_error(monkeypatch, tmp_path):
    with pytest.raises(SystemExit) as exc:
        entry.load_deployment(ROOT / "shared/deployments/monad-testnet.json")
    assert "not deployed" in str(exc.value)

    # main() stops there, before touching the RPC or the keys.
    monkeypatch.setenv("MONAD_RPC", "http://127.0.0.1:9")
    monkeypatch.setenv("REPORTER_KEYS", Account.create().key.hex())
    monkeypatch.setattr(entry, "Web3", lambda *a, **k: pytest.fail("must not connect"))
    with pytest.raises(SystemExit) as exc:
        entry.main()
    assert "not deployed" in str(exc.value)

    ok = tmp_path / "dep.json"
    ok.write_text(json.dumps({"chainId": 10143, "address": "0x" + "ab" * 20, "deployBlock": 0}))
    assert entry.load_deployment(ok)["deployBlock"] == 0  # block 0 is a valid deploy block


# ---------------------------------------------------------------- security review fixes

def ready(env):
    """A rental of prov_a whose slot 0 is probed and about to complete (reporter keys[1])."""
    start = env.chain.now() + 50
    rid = env.create(env.prov_a, start)
    svc = env.service()
    env.run(svc, start, start + 25)
    return start, rid, svc


def capture_sends(env, monkeypatch):
    """The node accepts every raw tx and holds it: nothing is mined. Returns the raw txs."""
    raws = []
    monkeypatch.setattr(env.w3.eth, "send_raw_transaction", lambda raw: raws.append(raw) or bytes([len(raws)]) * 32)
    return raws


def test_m2_gas_estimate_above_cap_is_refused_then_retried(env, monkeypatch, capsys):
    start, rid, svc = ready(env)
    env.warp(start + INTERVAL)
    estimate = env.c.functions.report_uptime(rid, 0, True).estimate_gas({"from": env.keys[1].address})
    assert estimate * 12 // 10 * 3 // 2 < chain_mod.GAS_CAP  # the real report keeps >= 1.5x headroom

    with monkeypatch.context() as m:
        raws = capture_sends(env, m)
        m.setattr(env.w3.eth, "estimate_gas", lambda *a, **k: 10_000_000)
        env.tick(svc)
        env.tick(svc, start + INTERVAL + 5)
        assert raws == []  # nothing signed or broadcast, not a clamped tx either
    rep = svc.state.reports[(rid, 0)]
    assert rep.tx is None and not rep.done and env.nonce(1) == 0 and env.slots(rid)[0] == 0
    assert env.chain.nonces.get(env.keys[1].address) is None  # tracker did not advance
    out = capsys.readouterr().out
    assert out.count(f"report-error rental={rid} slot=0") == 2 and "exceeds GAS_CAP" in out

    env.tick(svc, start + INTERVAL + 10)  # estimate is sane again: an ordinary retry
    assert env.slots(rid)[0] == UP and env.nonce(1) == 1


def test_m2_base_fee_above_cap_is_refused(env, monkeypatch, capsys):
    start, rid, svc = ready(env)
    env.warp(start + INTERVAL)
    real = env.w3.eth.get_block
    monkeypatch.setattr(env.w3.eth, "get_block", lambda *a, **k: {
        **real(*a, **k), "baseFeePerGas": chain_mod.MAX_BASE_FEE_WEI + 1})
    raws = capture_sends(env, monkeypatch)
    env.tick(svc)

    assert raws == [] and svc.state.reports[(rid, 0)].tx is None
    assert env.nonce(1) == 0 and env.slots(rid)[0] == 0
    assert "exceeds MAX_BASE_FEE_WEI" in capsys.readouterr().out


def test_m3_stuck_tx_is_replaced_at_same_nonce_and_never_after_slot_is_onchain(env, monkeypatch):
    start, rid, svc = ready(env)
    broadcast = env.w3.eth.send_raw_transaction
    raws = capture_sends(env, monkeypatch)  # faked mempool: txs are held, never mined
    decode = lambda raw: TypedTransaction.from_bytes(raw).as_dict()

    env.tick(svc, start + INTERVAL)
    rep = svc.state.reports[(rid, 0)]
    first = decode(raws[0])
    assert len(raws) == 1 and (rep.nonce, first["nonce"]) == (0, 0)

    svc.state.rentals[rid].force_down([0])  # too late: a tx is out, the verdict is fixed
    env.tick(svc, start + INTERVAL + service.PENDING_TIMEOUT_S)  # no receipt: replace
    second = decode(raws[1])
    assert len(raws) == 2 and second["nonce"] == first["nonce"] == rep.nonce
    assert second["maxFeePerGas"] >= first["maxFeePerGas"] * 11 // 10  # geth's minimum bump
    assert second["maxPriorityFeePerGas"] >= first["maxPriorityFeePerGas"] * 11 // 10
    assert second["data"] == first["data"]  # same slot, same verdict
    assert rep.fees == (second["maxFeePerGas"], second["maxPriorityFeePerGas"])
    assert env.chain.nonces[env.keys[1].address] == 1  # a replacement uses no new nonce

    broadcast(raws[0])  # the ORIGINAL lands after all; our tracked hash is the replacement
    assert env.slots(rid)[0] == UP and env.nonce(1) == 1
    env.run(svc, start + INTERVAL + 2 * service.PENDING_TIMEOUT_S, start + INTERVAL + 3 * service.PENDING_TIMEOUT_S)
    assert rep.done and rep.up is True
    # Later slots completed in that run and got their own nonces; slot 0 got no third tx.
    later = [decode(r) for r in raws[2:]]
    assert later and all(t["nonce"] > 0 and t["data"] != first["data"] for t in later)
    with pytest.raises(Exception):  # and the replacement can no longer be mined
        broadcast(raws[1])
    assert len([e for e in env.reported() if e["slot"] == 0]) == 1


def test_m3_reverted_or_spent_nonce_falls_back_to_a_fresh_nonce(env, monkeypatch):
    """The stuck tx's nonce was mined by another tx and the slot is still empty."""
    start, rid, svc = ready(env)
    with monkeypatch.context() as m:
        capture_sends(env, m)
        env.tick(svc, start + INTERVAL)
    rep = svc.state.reports[(rid, 0)]
    assert rep.nonce == 0
    key = env.keys[1]
    env.w3.eth.send_raw_transaction(key.sign_transaction({  # nonce 0 is spent elsewhere
        "to": key.address, "value": 0, "nonce": 0, "gas": 21_000, "chainId": env.chain.chain_id,
        "maxFeePerGas": 10**10, "maxPriorityFeePerGas": 10**9}).raw_transaction)

    env.tick(svc, start + INTERVAL + service.PENDING_TIMEOUT_S)
    assert env.slots(rid)[0] == UP and rep.nonce == 1
    assert env.w3.eth.get_transaction(rep.tx)["nonce"] == 1


def test_l2_rescanned_chunk_keeps_tracked_rental_state(env):
    start = env.chain.now() + 50
    rid = env.create(env.prov_a, start)
    svc = env.service()
    env.status["a.test"] = 503
    env.tick(svc, start)  # tracked, one failed probe in slot 0
    rental = svc.state.rentals[rid]
    rental.force_down([2])
    assert rental.probes == {0: [0, 1]}

    svc.state.last_block = env.deploy_block - 1  # e.g. a failed getLogs made the range repeat
    env.status["a.test"] = 200
    env.tick(svc, start + 5)
    assert svc.state.rentals[rid] is rental
    assert rental.probes == {0: [1, 2]} and rental.forced_down == {2}


@pytest.mark.parametrize("body, bad", [
    ('"0x1234" = "http://127.0.0.1:8081"', "0x1234"),
    ('"not-an-address" = "http://127.0.0.1:8081"', "not-an-address"),
    ('"0x00000000000000000000000000000000000000a1" = "ftp://127.0.0.1"', "0x00000000000000000000000000000000000000a1"),
    ('"0x00000000000000000000000000000000000000a1" = "127.0.0.1:8081"', "0x00000000000000000000000000000000000000a1"),
    ('"0x00000000000000000000000000000000000000a1" = 8081', "0x00000000000000000000000000000000000000a1"),
])
def test_l4_config_with_bad_address_or_url_fails_naming_the_key(tmp_path, body, bad):
    path = tmp_path / "config.toml"
    path.write_text("[nodes]\n" + body + "\n")
    with pytest.raises(ValueError, match=bad) as exc:
        config.load_nodes(path)
    assert "[nodes] key" in str(exc.value)


def test_l4_example_config_still_loads():
    nodes = config.load_nodes(ROOT / "oracle" / "config.example.toml")
    assert nodes == {"0x" + "0" * 38 + "a1": "http://127.0.0.1:8081", "0x" + "0" * 38 + "b2": "http://127.0.0.1:8082"}


def test_l7_malformed_reporter_key_exits_without_echoing_it(monkeypatch, capsys):
    secret = "0xdeadbeefNOTAKEYc0ffee1234567890"
    monkeypatch.setattr(entry, "load_deployment", lambda: {"chainId": 10143, "address": "0x" + "ab" * 20, "deployBlock": 0})
    monkeypatch.setattr(entry, "Web3", lambda *a, **k: pytest.fail("must not connect"))
    monkeypatch.setenv("MONAD_RPC", "http://127.0.0.1:9")
    monkeypatch.setenv("REPORTER_KEYS", f"{Account.create().key.hex()},{secret}")
    with pytest.raises(SystemExit) as exc:
        entry.main()
    captured = capsys.readouterr()
    text = f"{exc.value} {exc.value.__cause__} {exc.value.__context__ if not exc.value.__suppress_context__ else ''}"
    assert "invalid private key" in str(exc.value)
    for leak in (secret, secret[2:], "NOTAKEY"):
        assert leak not in text and leak not in captured.out + captured.err


def test_l3_rpc_error_text_is_not_logged(env, monkeypatch, capsys):
    start, rid, svc = ready(env)
    leak = "https://rpc.example/v1/SECRET-API-TOKEN"

    def boom(*a, **k):
        raise ConnectionError(f"HTTPSConnectionPool: {leak}")

    with monkeypatch.context() as m:
        m.setattr(env.w3.eth, "send_raw_transaction", boom)  # report-error
        m.setattr(env.chain, "rental_created", boom)         # discover-error
        env.tick(svc, start + INTERVAL)
    out = capsys.readouterr().out
    assert f"report-error rental={rid} slot=0" in out and "discover-error ConnectionError" in out
    assert "SECRET" not in out and "rpc.example" not in out
