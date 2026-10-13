"""Health probe of a provider node (SPEC H-3, H-7)."""
from __future__ import annotations

import asyncio
import time

import httpx

TIMEOUT_S = 2.0  # H-3: total budget for one probe, connect through body


async def probe(client: httpx.AsyncClient, url: str, provider: str = "") -> tuple[bool, float]:
    """GET <url>/health. ok only for HTTP 200 within TIMEOUT_S; never raises.

    Returns (ok, latency_ms) and writes one stdout log line (H-7).
    """
    t0 = time.monotonic()
    try:
        # wait_for bounds the whole request; httpx's own timeout is per phase.
        resp = await asyncio.wait_for(client.get(url.rstrip("/") + "/health"), TIMEOUT_S)
        ok, detail = resp.status_code == 200, f"status={resp.status_code}"
    except Exception as exc:  # timeout, refused, DNS, bad URL: all a failed probe
        ok, detail = False, f"error={type(exc).__name__}"
    latency_ms = (time.monotonic() - t0) * 1000
    print(f"probe provider={provider} url={url} ok={ok} latency_ms={latency_ms:.0f} {detail}", flush=True)
    return ok, latency_ms
