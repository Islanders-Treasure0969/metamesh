"""FastMCP entry point for metamesh.

Run with:
    uv run python -m metamesh.server
"""
from __future__ import annotations

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from metamesh.tools.add_concept import register as register_add_concept


def _ontology_root() -> Path:
    env = os.environ.get("METAMESH_ONTOLOGY_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    # Default: <repo>/ontology relative to this file (src/metamesh/server.py)
    return (Path(__file__).resolve().parents[2] / "ontology").resolve()


mcp = FastMCP("metamesh")
register_add_concept(mcp, ontology_root=_ontology_root())


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
