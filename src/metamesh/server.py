"""FastMCP entry point for metamesh.

Run with:
    METAMESH_ONTOLOGY_ROOT=/path/to/your/ontology \\
        uv run python -m metamesh.server

`METAMESH_ONTOLOGY_ROOT` must point at a directory that holds
``concepts/`` and ``relationships/`` subdirs (created on first write
if missing). The variable is required: metamesh is a framework, not
an application — the location of the ontology data is intentionally
external to this package.

For a worked example of an ontology directory layout, see
https://github.com/Islanders-Treasure0969/vtuber-analytics
"""
from __future__ import annotations

import os
import sys
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
    if not env:
        sys.stderr.write(
            "METAMESH_ONTOLOGY_ROOT is not set.\n"
            "metamesh is a framework — the ontology directory location is\n"
            "application-specific and must be provided by the caller. Set the\n"
            "env var to a directory that holds (or will hold) `concepts/` and\n"
            "`relationships/` subdirs.\n"
            "\n"
            "Examples:\n"
            "  export METAMESH_ONTOLOGY_ROOT=$HOME/my-ontology\n"
            "\n"
            "  # VTuber demo ontology (separate repo):\n"
            "  git clone https://github.com/Islanders-Treasure0969/vtuber-analytics\n"
            "  export METAMESH_ONTOLOGY_ROOT=$PWD/vtuber-analytics/ontology\n"
        )
        raise SystemExit(2)
    return Path(env).expanduser().resolve()


mcp = FastMCP("metamesh")


def _register_tools(root: Path) -> None:
    register_add_concept(mcp, ontology_root=root)
    register_add_relationship(mcp, ontology_root=root)
    register_query_concept(mcp, ontology_root=root)
    register_generate_dbt_yaml(mcp, ontology_root=root)
    register_generate_semantic_layer(mcp, ontology_root=root)
    register_export_llm_context(mcp, ontology_root=root)


def main() -> None:
    # Resolve the ontology root only when actually starting the server.
    # Importing the module (e.g. for testing other parts of the package)
    # must not require METAMESH_ONTOLOGY_ROOT to be set.
    _register_tools(_ontology_root())
    mcp.run()


if __name__ == "__main__":
    main()
