"""Oracle config: provider address -> node URL (SPEC H-2)."""
from __future__ import annotations

import tomllib
from urllib.parse import urlsplit

from web3 import Web3


def load_nodes(path) -> dict[str, str]:
    """The [nodes] table of a config file, keyed by lower-cased provider address."""
    with open(path, "rb") as f:
        nodes = tomllib.load(f).get("nodes", {})
    for addr, url in nodes.items():
        if not Web3.is_address(addr):
            raise ValueError(f"{path}: [nodes] key {addr!r} is not a valid address")
        parts = urlsplit(url) if isinstance(url, str) else None
        if not parts or parts.scheme not in ("http", "https") or not parts.netloc:
            raise ValueError(f"{path}: [nodes] key {addr!r} must map to an http(s) URL")
    return {addr.lower(): url for addr, url in nodes.items()}


def node_url(nodes: dict[str, str], provider: str) -> str | None:
    """URL of the provider's node, or None: such a rental is not probed or tracked."""
    return nodes.get(provider.lower())
