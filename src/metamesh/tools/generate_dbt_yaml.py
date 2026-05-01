"""generate_dbt_yaml MCP tool.

Reads the metamesh ontology and emits a dbt schema.yml fragment that can
be merged into an existing dbt project. Each Concept / Relationship maps
to one entry under ``models:`` with a Markdown ``description`` and a
``meta`` block carrying the ontology id and DV/Kimball extensions.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from mcp.server.fastmcp import FastMCP

from metamesh.generators.dbt_yaml import generate_dbt_yaml as _build


def _str_presenter(dumper: yaml.SafeDumper, data: str) -> yaml.ScalarNode:
    """Use literal block style ``|`` for multiline strings (readable descriptions)."""
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.SafeDumper.add_representer(str, _str_presenter)


def register(mcp: FastMCP, *, ontology_root: Path) -> None:
    @mcp.tool()
    def generate_dbt_yaml(
        output_path: str,
        naming: str = "dv_lower",
    ) -> str:
        """Emit a dbt schema.yml fragment from the current ontology.

        Args:
            output_path: 出力先パス (拡張子は ``.yml`` 想定)。親ディレクトリが
                無ければ作成する。
            naming: モデル名の生成戦略。
                - ``"as_is"``: ontology @id をそのまま使う (例: ``Streamer``)
                - ``"dv_lower"`` (default): ``dv:hub`` / ``dv:link`` があれば
                  小文字化して使う (例: ``hub_streamer``, ``lnk_collab``)。
                  無ければ snake_case にフォールバック
                - ``"snake"``: 常に snake_case (例: ``streamer``)

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
