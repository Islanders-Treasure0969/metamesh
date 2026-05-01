"""generate_semantic_layer MCP tool.

Reads the metamesh ontology and emits a dbt MetricFlow YAML fragment
that can be merged into an existing dbt project's semantic_models/.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from mcp.server.fastmcp import FastMCP

from metamesh.generators.semantic_layer import (
    generate_semantic_layer as _build,
)


def _str_presenter(dumper: yaml.SafeDumper, data: str) -> yaml.ScalarNode:
    """Use literal block style ``|`` for multiline strings (readable descriptions)."""
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.SafeDumper.add_representer(str, _str_presenter)


def register(mcp: FastMCP, *, ontology_root: Path) -> None:
    @mcp.tool()
    def generate_semantic_layer(
        output_path: str,
        naming: str = "dv_lower",
    ) -> str:
        """Emit a MetricFlow semantic_models YAML fragment from the ontology.

        Args:
            output_path: 出力先パス。親ディレクトリが無ければ作成する。
            naming: モデル名の生成戦略 (``"as_is"`` / ``"dv_lower"`` / ``"snake"``)。
                ``generate_dbt_yaml`` と揃えると、生成された semantic_models が
                同じ dbt model を ``ref()`` で参照できる。

        Returns:
            書き込んだファイルへの絶対パス。
        """
        doc = _build(ontology_root=ontology_root, naming=naming)
        out = Path(output_path).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                doc,
                f,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
                indent=2,
            )
        return f"Wrote: {out}"
