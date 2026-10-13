"""T-018 (SPEC H-8, H-9; D-11, D-13): renter allow-list and per-rental report budget.

Same fixtures as test_service.py: the real contract on the in-process eth-tester chain,
keys generated in conftest.py, time travel instead of waiting.
"""
import pytest
from eth_account import Account
from eth_account.typed_transactions import TypedTransaction
from fastapi.testclient import TestClient

import oracle.__main__ as entry
from oracle import config, service
from oracle.api import create_app
from oracle.tests.conftest import GRACE, INTERVAL, N, ROOT, UP

PAST_END = N * INTERVAL + GRACE + 10  # offset from start, after reporting closed
PLACEHOLDER = "0x00000000000000000000000000000000000000a1"


def spy(env, monkeypatch):
    """Record (name, rental_id) for every per-rental call on the chain wrapper."""
    calls = []
    for name in ("get_slots", "send_report", "account_for"):
        real = getattr(env.chain, name)
        monkeypatch.setattr(env.chain, name,
                            lambda *a, _n=name, _real=real: calls.append((_n, a[0])) or _real(*a))
    return calls


def write(tmp_path, body):
    path = tmp_path / "config.toml"
    path.write_text(body)
    return path


# ---------------------------------------------------------------- H-8 renter allow-list

def test_h8_listed_renter_is_served_and_match_is_case_insensitive(env, tmp_path):
    shouting = "0x" + env.renter[2:].upper()
    assert shouting != env.renter != env.renter.lower()  # the event carries the checksummed form
    env.renters = config.load_renters(write(tmp_path, f'[renters]\nallow = ["{shouting}"]\n'))
    assert env.renters == {env.renter.lower()}

    start = env.chain.now() + 50
    rid = env.create(env.prov_a, start)
    svc = env.service()
    env.run(svc, start, start + INTERVAL)
    assert rid in svc.state.rentals and env.slots(rid)[0] == UP


def test_h8_unlisted_renter_is_ignored_with_no_get_slots_no_probe_and_no_tx(env, monkeypatch, capsys):
    start = env.chain.now() + 50
    rid = env.create(env.prov_a, start, renter=env.outsider)  # configured, healthy provider
    calls = spy(env, monkeypatch)
    svc = env.service()
    env.run(svc, start, start + PAST_END)

    assert calls == []  # no get_slots, no send, not even a key lookup
    assert env.probes == []
    assert rid not in svc.state.rentals and not svc.state.reports
    assert env.slots(rid) == [0] * N and env.reported() == []
    assert env.nonce(0) == env.nonce(1) == 0
    out = capsys.readouterr().out
    assert out.count(f"ignore rental={rid} renter={env.outsider} reason=renter-not-allowed") == 1
    assert "tx hash=" not in out and "track rental=" not in out


def test_h8_unlisted_renter_rental_is_absent_from_control_api(env):
    start = env.chain.now() + 50
    served = env.create(env.prov_a, start)
    ignored = env.create(env.prov_a, start, renter=env.outsider)
    svc = env.service()
    env.run(svc, start, start + INTERVAL)
    api = TestClient(create_app(svc), base_url="http://127.0.0.1:8787")

    assert [r["rentalId"] for r in api.get("/rentals").json()] == [served]
    assert api.get(f"/rentals/{served}").status_code == 200
    assert api.get(f"/rentals/{ignored}").status_code == 404
    assert api.post(f"/rentals/{ignored}/force-down", json={"slots": [0]}).status_code == 404


@pytest.mark.parametrize("body", ["", "[nodes]\n", "[renters]\n", "[renters]\nallow = []\n"],
                         ids=["empty-file", "no-renters-section", "no-allow-key", "empty-allow"])
def test_h8_missing_or_empty_allow_list_serves_nobody_and_warns(env, tmp_path, capsys, body):
    env.renters = config.load_renters(write(tmp_path, body))
    assert env.renters == set()

    start = env.chain.now() + 50
    rid = env.create(env.prov_a, start)  # the demo renter, a configured provider
    svc = env.service()
    out = capsys.readouterr().out
    assert out.count("WARNING renter allow-list is empty") == 1 and "no rental will be served" in out

    env.run(svc, start, start + PAST_END)
    assert not svc.state.rentals and env.probes == []
    assert env.slots(rid) == [0] * N and env.nonce(0) == env.nonce(1) == 0
    assert f"ignore rental={rid} renter={env.renter} reason=renter-not-allowed" in capsys.readouterr().out


def test_h8_non_empty_allow_list_prints_no_warning(env, capsys):
    env.service()
    assert "WARNING" not in capsys.readouterr().out


@pytest.mark.parametrize("allow, bad", [
    ('["0x1234"]', "0x1234"),
    ('["not-an-address"]', "not-an-address"),
    (f'["{PLACEHOLDER}", "0xZZ00000000000000000000000000000000000000"]', "0xZZ0000"),
    (f'["{PLACEHOLDER}", 5]', "5"),
])
def test_h8_invalid_allow_list_entry_fails_at_load_naming_it(tmp_path, allow, bad):
    with pytest.raises(ValueError, match=bad) as exc:
        config.load_renters(write(tmp_path, f"[renters]\nallow = {allow}\n"))
    assert "[renters] allow" in str(exc.value)


def test_h8_allow_that_is_not_a_list_fails_at_load(tmp_path):
    # A bare string would otherwise be read as a list of characters.
    with pytest.raises(ValueError, match=r"\[renters\] allow must be a list"):
        config.load_renters(write(tmp_path, f'[renters]\nallow = "{PLACEHOLDER}"\n'))


def test_h8_bad_allow_list_stops_main_before_any_network_access(tmp_path, monkeypatch):
    monkeypatch.setattr(entry, "load_deployment", lambda: {"chainId": 10143, "address": "0x" + "ab" * 20, "deployBlock": 0})
    monkeypatch.setattr(entry, "Web3", lambda *a, **k: pytest.fail("must not connect"))
    monkeypatch.setenv("MONAD_RPC", "http://127.0.0.1:9")
    monkeypatch.setenv("REPORTER_KEYS", Account.create().key.hex())
    monkeypatch.setenv("ORACLE_CONFIG", str(write(tmp_path, '[renters]\nallow = ["0xnope"]\n')))
    with pytest.raises(SystemExit) as exc:
        entry.main()
    assert str(exc.value).startswith("oracle: ") and "0xnope" in str(exc.value)


def test_h8_example_config_has_a_placeholder_renter():
    assert config.load_renters(ROOT / "oracle" / "config.example.toml") == {"0x" + "0" * 38 + "c3"}


def test_h8_provider_gate_and_renter_gate_are_cumulative(env, monkeypatch, capsys):
    start = env.chain.now() + 50
    both = env.create(env.prov_a, start)                              # listed renter, known provider
    no_node = env.create(env.stranger, start)                         # listed renter, unknown provider
    no_renter = env.create(env.prov_b, start, renter=env.outsider)    # unlisted renter, known provider
    neither = env.create(env.stranger, start, renter=env.outsider)
    calls = spy(env, monkeypatch)
    svc = env.service()
    env.run(svc, start, start + PAST_END)

    assert set(svc.state.rentals) == {both}
    assert {rid for _, rid in calls} == {both}
    assert set(env.probes) == {"a.test"}  # prov_b's node is configured but its only rental is ignored
    assert env.slots(both) == [UP] * N
    assert all(env.slots(rid) == [0] * N for rid in (no_node, no_renter, neither))
    out = capsys.readouterr().out
    assert out.count(f"ignore rental={no_node} ") == out.count(f"ignore rental={no_renter} ") == 1
    assert out.count(f"ignore rental={neither} ") == 1  # one line per ignored rental, not one per gate
    assert f"ignore rental={no_node} provider={env.stranger} reason=no-node-in-config" in out
    assert f"ignore rental={no_renter} renter={env.outsider} reason=renter-not-allowed" in out


# ---------------------------------------------------------------- H-9 report budget

def flaky(env, monkeypatch, fails):
    """Chain stub: a send for which fails(rental_id, slot) is true is broadcast, gets a
    hash, and is then seen reverted (status 0), so the service re-sends it on the next
    tick. Every other send goes to the real chain. Returns the list of broadcasts."""
    real_send, real_status, sent = env.chain.send_report, env.chain.receipt_status, []

    def send(rid, k, up, replace=None):
        sent.append((rid, k))
        if fails(rid, k):
            return f"0xdead{len(sent):060x}", 0, 0, 0
        return real_send(rid, k, up, replace)

    monkeypatch.setattr(env.chain, "send_report", send)
    monkeypatch.setattr(env.chain, "receipt_status",
                        lambda h: 0 if h.startswith("0xdead") else real_status(h))
    return sent


def test_h9_healthy_four_slot_rental_uses_exactly_four_broadcasts(env, monkeypatch, capsys):
    start = env.chain.now() + 50
    rid = env.create(env.prov_a, start)
    raws, real = [], env.w3.eth.send_raw_transaction
    monkeypatch.setattr(env.w3.eth, "send_raw_transaction", lambda raw: raws.append(raw) or real(raw))
    svc = env.service()
    env.run(svc, start, start + PAST_END)

    assert len(raws) == N == env.nonce(1)
    assert env.slots(rid) == [UP] * N
    assert "budget-spent" not in capsys.readouterr().out


@pytest.mark.parametrize("failing", [(0,), (0, 2)], ids=["slot-0-fails", "slots-0-and-2-fail"])
def test_h9_resubmissions_stop_after_n_extra_and_other_slots_still_get_their_first_report(
        env, monkeypatch, capsys, failing):
    start = env.chain.now() + 50
    rid = env.create(env.prov_a, start)
    sent = flaky(env, monkeypatch, lambda r, k: k in failing)
    svc = env.service()
    env.run(svc, start, start + PAST_END)

    # Slot 0: first send at +30, re-sent at +35..+50 (N = 4 extra), refused from +55 on,
    # i.e. before slots 1..3 even complete - their first sends are still allowed.
    assert sent[:N + 1] == [(rid, 0)] * (N + 1)
    assert sent.count((rid, 0)) == N + 1
    assert all(sent.count((rid, k)) == 1 for k in (1, 2, 3))  # incl. a failing slot 2: no retry left
    assert len(sent) == 2 * N  # total broadcasts <= 2N
    ok = [k for k in range(N) if k not in failing]
    assert env.slots(rid) == [0 if k in failing else UP for k in range(N)]
    assert env.nonce(1) == len(ok)
    assert all(svc.state.reports[(rid, k)].gave_up for k in failing)
    assert all(svc.state.reports[(rid, k)].done for k in ok)
    out = capsys.readouterr().out
    assert out.count("budget-spent") == 1  # once per rental, not per slot or per tick
    assert f"budget-spent rental={rid} used={N + 1}/{2 * N}" in out
    assert "reason=reporting-closed" not in out  # the budget ended the retries first (H-4 bound)


@pytest.mark.parametrize("refusal", ["gas-cap", "rpc-error"])
def test_h9_send_refused_before_broadcast_does_not_consume_budget(env, monkeypatch, capsys, refusal):
    start = env.chain.now() + 50
    rid = env.create(env.prov_a, start)
    svc = env.service()
    env.run(svc, start, start + 25)

    def boom(raw):
        raise ConnectionError("rpc down")

    with monkeypatch.context() as m:
        if refusal == "gas-cap":  # SendRefused, raised before anything is signed
            m.setattr(env.w3.eth, "estimate_gas", lambda *a, **k: 10_000_000)
        else:  # the node never took the tx
            m.setattr(env.w3.eth, "send_raw_transaction", boom)
        env.run(svc, start + INTERVAL, start + INTERVAL + 25)  # 6 attempts > 1 + N
    out = capsys.readouterr().out
    assert out.count(f"report-error rental={rid} slot=0") == 6
    assert env.nonce(1) == 0 and not svc.state.reports[(rid, 0)].gave_up

    env.run(svc, start + 2 * INTERVAL, start + PAST_END)
    assert env.slots(rid) == [UP] * N and env.nonce(1) == N
    assert "budget-spent" not in out + capsys.readouterr().out


def test_h9_same_nonce_fee_replacement_consumes_budget(env, monkeypatch, capsys):
    start = env.chain.now() + 50
    rid = env.create(env.prov_a, start)
    monkeypatch.setattr(service, "PENDING_TIMEOUT_S", 5)  # replace a pending tx on every tick
    raws = []  # faked mempool: every tx is accepted and held, none is mined
    monkeypatch.setattr(env.w3.eth, "send_raw_transaction", lambda raw: raws.append(raw) or bytes([len(raws)]) * 32)
    svc = env.service()
    env.run(svc, start, start + PAST_END)

    txs = [TypedTransaction.from_bytes(raw).as_dict() for raw in raws]
    # Slot 0: one send + N replacements at nonce 0, then the pool is empty. Slots 1..3:
    # one first send each on fresh nonces, and no replacement for them.
    assert [t["nonce"] for t in txs] == [0] * (N + 1) + [1, 2, 3]
    assert len({t["data"] for t in txs[:N + 1]}) == 1
    fees = [t["maxFeePerGas"] for t in txs[:N + 1]]
    assert fees == sorted(set(fees))  # each replacement really out-bid the previous one
    assert env.nonce(1) == 0 and env.slots(rid) == [0] * N
    out = capsys.readouterr().out
    assert out.count("replaces-nonce=0") == N
    assert out.count("budget-spent") == 1 and f"budget-spent rental={rid} used={N + 1}/{2 * N}" in out


def test_h9_budget_is_per_rental(env, monkeypatch, capsys):
    start = env.chain.now() + 50
    r1, r2 = env.create(env.prov_a, start), env.create(env.prov_b, start)
    # Every send of r1 fails. r2's slot 3 fails once, long after r1's pool ran dry.
    sent = flaky(env, monkeypatch, lambda rid, k: rid == r1 or ((rid, k) == (r2, 3) and sent.count((r2, 3)) == 1))
    svc = env.service()
    env.run(svc, start, start + PAST_END)

    assert len([s for s in sent if s[0] == r1]) == 2 * N and env.slots(r1) == [0] * N
    assert sent.count((r2, 3)) == 2  # r2 still had its own re-submission
    assert env.slots(r2) == [UP] * N
    out = capsys.readouterr().out
    assert out.count(f"budget-spent rental={r1} ") == 1 and f"budget-spent rental={r2} " not in out
