"""Local-only tests for scripts/deploy.py.

Chain: web3's in-process EthereumTesterProvider. Keys: generated here. Output: tmp_path.
Nothing in this file touches a network or the real shared/deployments file.
"""
import json

import pytest
from eth_account import Account
from web3 import EthereumTesterProvider, Web3

import deploy as d

REAL_OUT = d.OUT_PATH.read_bytes()
KEYS = {"chainId", "address", "deployBlock", "reporters", "reportGrace", "challengeWindow", "deployedAt", "commit"}


@pytest.fixture(autouse=True)
def real_deployment_file_untouched():
    yield
    assert d.OUT_PATH.read_bytes() == REAL_OUT


@pytest.fixture
def chain():
    w3 = Web3(EthereumTesterProvider())
    deployer = Account.create()
    h = w3.eth.send_transaction({"from": w3.eth.accounts[0], "to": deployer.address, "value": w3.to_wei(100, "ether")})
    w3.eth.wait_for_transaction_receipt(h)
    return w3, deployer


def reporters(n=2):
    return [Account.create().address for _ in range(n)]


def run(chain, out, reps=None, **kw):
    w3, deployer = chain
    return d.deploy(w3, deployer, reps or reporters(), out, expected_chain_id=w3.eth.chain_id, **kw)


def test_deploy_writes_json_and_allowlists_reporters(chain, tmp_path):
    w3, deployer = chain
    out, reps = tmp_path / "dep.json", reporters(3)
    run(chain, out, reps)

    rec = json.loads(out.read_text())
    assert set(rec) == KEYS
    assert rec["chainId"] == w3.eth.chain_id
    assert rec["address"] == Web3.to_checksum_address(rec["address"])
    assert len(w3.eth.get_code(rec["address"])) > 0
    assert rec["deployBlock"] == w3.eth.block_number
    assert rec["reporters"] == reps
    assert (rec["reportGrace"], rec["challengeWindow"]) == (30, 60)
    assert rec["deployedAt"].endswith("Z") and len(rec["commit"]) >= 40

    c = w3.eth.contract(address=rec["address"], abi=json.loads(d.ABI_PATH.read_text()))
    assert c.functions.next_rental_id().call() == 1
    assert all(c.functions.is_reporter(r).call() for r in reps)
    assert not c.functions.is_reporter(deployer.address).call()


def test_wrong_chain_id_refused_before_any_tx(chain, tmp_path):
    w3, deployer = chain
    out = tmp_path / "dep.json"
    with pytest.raises(SystemExit, match="wrong chain id"):
        d.deploy(w3, deployer, reporters(), out)  # default expected_chain_id = 10143
    assert w3.eth.get_transaction_count(deployer.address) == 0
    assert not out.exists()


def test_existing_deployment_needs_force(chain, tmp_path):
    w3, deployer = chain
    out = tmp_path / "dep.json"
    first = run(chain, out)
    with pytest.raises(SystemExit, match="--force"):
        run(chain, out)
    assert json.loads(out.read_text()) == first
    assert w3.eth.get_transaction_count(deployer.address) == 1
    assert run(chain, out, force=True)["address"] != first["address"]


def test_placeholder_with_null_address_is_overwritten(chain, tmp_path):
    out = tmp_path / "dep.json"
    out.write_bytes(REAL_OUT)  # the checked-in placeholder: "address": null
    assert run(chain, out)["address"]


def test_stale_abi_aborts_before_any_tx(chain, tmp_path, monkeypatch):
    w3, deployer = chain
    stale = tmp_path / "abi.json"
    stale.write_text("[]")
    monkeypatch.setattr(d, "ABI_PATH", stale)
    with pytest.raises(SystemExit, match="interface-sync"):
        run(chain, tmp_path / "dep.json")
    assert w3.eth.get_transaction_count(deployer.address) == 0


@pytest.mark.parametrize(
    "reps, msg",
    [
        ([], "1..8"),
        (reporters(9), "1..8"),
        ([d.ZERO], "zero address"),
        (["0xnope"], "malformed"),
    ],
)
def test_bad_reporters_rejected_before_any_tx(chain, tmp_path, reps, msg):
    w3, deployer = chain
    with pytest.raises(SystemExit, match=msg):
        d.deploy(w3, deployer, reps, tmp_path / "dep.json", expected_chain_id=w3.eth.chain_id)
    assert w3.eth.get_transaction_count(deployer.address) == 0


def test_duplicate_reporter_rejected_case_insensitively():
    r = reporters(1)[0]
    with pytest.raises(SystemExit, match="duplicate"):
        d.check_reporters([r, r.lower()])


# ---- environment parsing (no chain, no network: main() exits before building a provider)
GOOD = "0x" + "11" * 32
SECRETS = ["0xdeadbeefNOTAKEY", "0x" + "ab" * 31, "0x" + "00" * 32]


@pytest.mark.parametrize("var", ["DEPLOYER_KEY", "REPORTER_KEYS"])
@pytest.mark.parametrize("bad", SECRETS)
def test_main_malformed_key_exits_without_echo(monkeypatch, capsys, var, bad):
    env = {"MONAD_RPC": "http://127.0.0.1:9", "DEPLOYER_KEY": GOOD, "REPORTER_KEYS": GOOD, var: bad}
    monkeypatch.delenv("REPORTER_ADDRESSES", raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    with pytest.raises(SystemExit) as e:
        d.main([])
    shown = str(e.value) + "".join(capsys.readouterr())
    assert var in shown
    assert bad not in shown and bad[2:] not in shown
    assert e.value.__cause__ is None and e.value.__suppress_context__  # no chained library message


def test_env_missing_variables():
    for missing in ("MONAD_RPC", "DEPLOYER_KEY"):
        env = {"MONAD_RPC": "x", "DEPLOYER_KEY": GOOD, "REPORTER_KEYS": GOOD}
        del env[missing]
        with pytest.raises(SystemExit, match=missing):
            d.read_env(env)
    with pytest.raises(SystemExit, match="REPORTER_KEYS or REPORTER_ADDRESSES"):
        d.read_env({"MONAD_RPC": "x", "DEPLOYER_KEY": GOOD})


def test_env_keys_and_addresses():
    a, b = Account.create(), Account.create()
    base = {"MONAD_RPC": "x", "DEPLOYER_KEY": GOOD}
    keys = f"{a.key.hex()}, {b.key.hex()}"
    assert d.read_env({**base, "REPORTER_KEYS": keys})[2] == [a.address, b.address]
    assert d.read_env({**base, "REPORTER_ADDRESSES": f"{a.address},{b.address.lower()}"})[2] == [a.address, b.address]
    assert d.read_env({**base, "REPORTER_KEYS": keys, "REPORTER_ADDRESSES": f"{b.address},{a.address}"})[2] == [
        a.address,
        b.address,
    ]
    with pytest.raises(SystemExit, match="do not describe the same"):
        d.read_env({**base, "REPORTER_KEYS": keys, "REPORTER_ADDRESSES": a.address})
    with pytest.raises(SystemExit, match="REPORTER_ADDRESSES") as e:
        d.read_env({**base, "REPORTER_ADDRESSES": a.key.hex()})  # a key pasted into the wrong variable
    assert a.key.hex() not in str(e.value)


# ---- security-review fixes (M-1, M-2, L-2, L-3, L-5)
def not_sent(chain, out):
    w3, deployer = chain
    assert w3.eth.get_transaction_count(deployer.address) == 0
    assert not out.exists()


def last_tx_hash(w3):
    return Web3.to_hex(w3.eth.get_block("latest")["transactions"][0])


def drop_base_fee(w3, monkeypatch):
    real = w3.eth.get_block
    monkeypatch.setattr(w3.eth, "get_block", lambda *a, **k: {x: v for x, v in real(*a, **k).items() if x != "baseFeePerGas"})


def test_inflated_gas_estimate_exits_before_signing(chain, tmp_path, monkeypatch):
    from web3.contract.contract import ContractConstructor

    monkeypatch.setattr(ContractConstructor, "estimate_gas", lambda self, *a, **k: d.GAS_CAP)  # x1.2 > cap
    with pytest.raises(SystemExit, match="GAS_CAP"):
        run(chain, tmp_path / "dep.json")
    not_sent(chain, tmp_path / "dep.json")


def test_inflated_base_fee_exits_before_signing(chain, tmp_path, monkeypatch):
    w3, _ = chain
    monkeypatch.setattr(w3.eth, "get_block", lambda *a, **k: {"baseFeePerGas": d.MAX_FEE_PER_GAS_WEI})  # x2 > cap
    with pytest.raises(SystemExit, match="MAX_FEE_PER_GAS_WEI"):
        run(chain, tmp_path / "dep.json")
    not_sent(chain, tmp_path / "dep.json")


def test_inflated_legacy_gas_price_exits_before_signing(chain, tmp_path, monkeypatch):
    w3, _ = chain
    drop_base_fee(w3, monkeypatch)
    monkeypatch.setattr(type(w3.eth), "gas_price", property(lambda self: d.MAX_FEE_PER_GAS_WEI + 1))
    with pytest.raises(SystemExit, match="MAX_FEE_PER_GAS_WEI"):
        run(chain, tmp_path / "dep.json")
    not_sent(chain, tmp_path / "dep.json")


def test_caps_have_headroom_over_the_real_limit(chain, tmp_path, capsys):
    run(chain, tmp_path / "dep.json", reporters(8))  # the most expensive constructor
    limit = int(capsys.readouterr().out.split("(limit ")[1].split(")")[0])
    assert limit < d.GAS_CAP <= 3 * limit
    assert d.MAX_FEE_PER_GAS_WEI >= 2 * 100 * 10**9  # 2x Monad's minimum base fee still fits


def test_legacy_gas_price_branch_deploys(chain, tmp_path, monkeypatch):
    w3, _ = chain
    drop_base_fee(w3, monkeypatch)
    rec = run(chain, tmp_path / "dep.json")
    tx = w3.eth.get_transaction(last_tx_hash(w3))
    assert tx["type"] == 0 and tx["gasPrice"] == w3.eth.gas_price
    assert len(w3.eth.get_code(rec["address"])) > 0


def test_status_0_receipt_prints_hash_and_writes_nothing(chain, tmp_path, monkeypatch, capsys):
    w3, _ = chain
    real, out = w3.eth.wait_for_transaction_receipt, tmp_path / "dep.json"
    monkeypatch.setattr(w3.eth, "wait_for_transaction_receipt", lambda *a, **k: {**real(*a, **k), "status": 0})
    with pytest.raises(SystemExit, match="reverted") as e:
        run(chain, out)
    tx_hash = last_tx_hash(w3)
    assert f"tx hash      {tx_hash}" in capsys.readouterr().out and tx_hash in str(e.value)
    assert not out.exists()


def test_failed_post_deploy_check_prints_hash_and_address_and_writes_nothing(chain, tmp_path, monkeypatch, capsys):
    w3, _ = chain
    out = tmp_path / "dep.json"
    monkeypatch.setattr(w3.eth, "get_code", lambda *a, **k: b"")
    with pytest.raises(SystemExit, match="post-deploy check failed: no code") as e:
        run(chain, out)
    shown, tx_hash = capsys.readouterr().out, last_tx_hash(w3)
    address = w3.eth.get_transaction_receipt(tx_hash)["contractAddress"]
    assert f"tx hash      {tx_hash}" in shown and f"address      {address}" in shown
    assert tx_hash in str(e.value) and address in str(e.value)
    assert not out.exists()


def test_receipt_timeout_repeats_hash_and_warns_against_rerun(chain, tmp_path, monkeypatch, capsys):
    from web3.exceptions import TimeExhausted

    w3, _ = chain
    out = tmp_path / "dep.json"

    def timeout(*a, **k):
        raise TimeExhausted("stub")

    monkeypatch.setattr(w3.eth, "wait_for_transaction_receipt", timeout)
    with pytest.raises(SystemExit, match="do NOT re-run blindly — check the explorer first") as e:
        run(chain, out)
    tx_hash = last_tx_hash(w3)
    assert tx_hash in str(e.value) and tx_hash in capsys.readouterr().out
    assert not out.exists()


@pytest.mark.parametrize("content", ["[]", '["0xabc"]', '"0xabc"', "null", "{not json", ""])
def test_non_object_deployment_file_needs_force(chain, tmp_path, content):
    w3, deployer = chain
    out = tmp_path / "dep.json"
    out.write_text(content)
    with pytest.raises(SystemExit, match="not a deployment record.*--force"):
        run(chain, out)
    assert out.read_text() == content
    assert w3.eth.get_transaction_count(deployer.address) == 0
    assert run(chain, out, force=True)["address"]


def test_unreachable_rpc_exits_without_showing_the_url(tmp_path, capsys):
    from web3.providers.base import BaseProvider

    secret = "http://rpc.invalid/v1/SECRET-API-KEY"

    class Dead(BaseProvider):  # raises in-process: no socket is opened
        def make_request(self, method, params):
            raise ConnectionError(f"cannot connect to {secret}")

    out = tmp_path / "dep.json"
    with pytest.raises(SystemExit) as e:
        d.deploy(Web3(Dead()), Account.create(), reporters(), out)
    assert str(e.value) == "cannot reach MONAD_RPC (value not shown)"
    assert "SECRET" not in str(e.value) + "".join(capsys.readouterr())
    assert e.value.__cause__ is None and e.value.__suppress_context__
    assert not out.exists()


def test_low_balance_warning_does_not_cite_the_reserve_rule(tmp_path, capsys):
    w3 = Web3(EthereumTesterProvider())
    poor = Account.create()
    w3.eth.wait_for_transaction_receipt(
        w3.eth.send_transaction({"from": w3.eth.accounts[0], "to": poor.address, "value": d.LOW_GAS_BALANCE_WEI - 1})
    )
    run((w3, poor), tmp_path / "dep.json")
    warning = [line for line in capsys.readouterr().out.splitlines() if "WARNING" in line and "wallet" in line]
    assert len(warning) == 1 and "low gas balance" in warning[0] and "reserve" not in warning[0]


def test_no_assert_used_as_runtime_check():
    import ast

    tree = ast.parse(open(d.__file__).read())
    assert not [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Assert)]
