"""FastMCP entry point for metamesh.

Run with:
    uv run python -m metamesh.server
"""
from __future__ import annotations

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from metamesh.tools.add_concept import register as register_add_concept
from metamesh.tools.add_relationship import register as register_add_relationship
from metamesh.tools.export_llm_context import register as register_export_llm_context
from metamesh.tools.generate_dbt_yaml import register as register_generate_dbt_yaml
from metamesh.tools.generate_semantic_layer import (
    register as register_generate_semantic_layer,
)
from metamesh.tools.query_concept import register as register_query_concept


def _ontology_root() -> Path:
    env = os.environ.get("METAMESH_ONTOLOGY_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    # Default: <repo>/ontology relative to this file (src/metamesh/server.py)
    return (Path(__file__).resolve().parents[2] / "ontology").resolve()


mcp = FastMCP("metamesh")
_root = _ontology_root()
register_add_concept(mcp, ontology_root=_root)
register_add_relationship(mcp, ontology_root=_root)
register_query_concept(mcp, ontology_root=_root)
register_generate_dbt_yaml(mcp, ontology_root=_root)
register_generate_semantic_layer(mcp, ontology_root=_root)
register_export_llm_context(mcp, ontology_root=_root)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
