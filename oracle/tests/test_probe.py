"""SPEC H-2, H-3, H-7: the health probe and the provider -> node URL config."""
import asyncio
import socket
from pathlib import Path

import httpx

from oracle.config import load_nodes, node_url
from oracle.probe import TIMEOUT_S, probe

URL = "http://node.test"


def run_probe(handler, url=URL, provider="0xabc"):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await probe(client, url, provider)

    return asyncio.run(go())


def test_probe_200_is_ok_and_hits_health_path():
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(200, json={"ok": True})

    ok, latency_ms = run_probe(handler, url=URL + "/")
    assert ok is True
    assert latency_ms >= 0
    assert seen == [URL + "/health"]


def test_probe_non_200_is_failed():
    for status in (204, 301, 404, 500, 503):
        ok, _ = run_probe(lambda request, s=status: httpx.Response(s))
        assert ok is False, status


def test_probe_timeout_over_2s_is_failed():
    assert TIMEOUT_S == 2.0

    async def slow(request):
        await asyncio.sleep(TIMEOUT_S + 1)
        return httpx.Response(200)

    ok, latency_ms = run_probe(slow)
    assert ok is False
    assert 1900 <= latency_ms < 2900  # cut off at the 2 s budget, not at the reply


def test_probe_connection_error_is_failed():
    with socket.socket() as s:  # a local port with nothing listening
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    async def go():
        async with httpx.AsyncClient() as client:
            return await probe(client, f"http://127.0.0.1:{port}")

    ok, _ = asyncio.run(go())
    assert ok is False


def test_probe_never_raises_on_bad_url():
    ok, _ = run_probe(lambda request: httpx.Response(200), url="not a url")
    assert ok is False


def test_probe_writes_one_log_line(capsys):
    run_probe(lambda request: httpx.Response(200))
    run_probe(lambda request: httpx.Response(503))
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 2
    assert lines[0].startswith(f"probe provider=0xabc url={URL} ok=True latency_ms=")
    assert lines[1].startswith(f"probe provider=0xabc url={URL} ok=False latency_ms=")


def test_provider_lookup_is_case_insensitive(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text('[nodes]\n"0xAbCdEf0000000000000000000000000000000001" = "http://127.0.0.1:8081"\n')
    nodes = load_nodes(cfg)
    assert node_url(nodes, "0xabcdef0000000000000000000000000000000001") == "http://127.0.0.1:8081"
    assert node_url(nodes, "0xABCDEF0000000000000000000000000000000001") == "http://127.0.0.1:8081"


def test_provider_without_node_has_no_url(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text('[nodes]\n"0x0000000000000000000000000000000000000001" = "http://127.0.0.1:8081"\n')
    assert node_url(load_nodes(cfg), "0x0000000000000000000000000000000000000002") is None
    cfg.write_text("")  # no [nodes] table at all
    assert load_nodes(cfg) == {}


def test_example_config_points_at_docker_nodes():
    nodes = load_nodes(Path(__file__).parents[1] / "config.example.toml")
    assert sorted(nodes.values()) == ["http://127.0.0.1:8081", "http://127.0.0.1:8082"]
