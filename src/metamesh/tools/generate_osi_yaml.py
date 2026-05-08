"""generate_osi_yaml MCP tool.

オントロジーを OSI (Open Semantic Interchange) v0.1.1 の YAML 形式で
書き出す。OSI 経由で BI / AI tool (Snowflake Cortex / dbt SL / Salesforce
等) に semantic model を流し込むための入口。

詳細仕様 / マッピング設計は metamesh.generators.osi の docstring 参照。
"""
from __future__ import annotations

from pathlib import Path

import yaml
from mcp.server.fastmcp import FastMCP

from metamesh.generators.osi import generate_osi_yaml as _build


def _str_presenter(dumper: yaml.SafeDumper, data: str) -> yaml.ScalarNode:
    """Use literal block style ``|`` for multiline strings (readable descriptions)."""
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.SafeDumper.add_representer(str, _str_presenter)


def register(mcp: FastMCP, *, ontology_root: Path) -> None:
    @mcp.tool()
    def generate_osi_yaml(
        output_path: str,
        naming: str = "dv_lower",
        source_template: str = "LOGICAL.{name}",
        source_overrides: dict[str, str] | None = None,
        model_name_override: str | None = None,
    ) -> str:
        """Emit an OSI (Open Semantic Interchange) v0.1.1 YAML from the current ontology.

        Args:
            output_path: 出力先パス (拡張子は ``.yaml`` 想定)。親ディレクトリが
                無ければ作成する。
            naming: Dataset 名の生成戦略。
                - ``"as_is"``: ontology @id をそのまま使う (例: ``Streamer``)
                - ``"dv_lower"`` (default): ``dv:hub`` / ``dv:link`` を小文字化して
                  使う (例: ``hub_streamer``, ``lnk_collab``)。無ければ snake_case
                - ``"snake"``: 常に snake_case (例: ``streamer``)
            source_template: ``Dataset.source`` のテンプレート。プレースホルダ
                ``{name}`` は dataset 名に置換される (default: ``LOGICAL.{name}``)。
                OSI は source を必須とするが、metamesh のオントロジーは logical
                only なので便宜的なプレースホルダを埋める。
            source_overrides: dataset 名 → 物理 source の差し替え dict。例:
                ``{"hub_streamer": "PROD.ANALYTICS.HUB_STREAMER"}``
            model_name_override: 上位 SemanticModel の name の上書き。指定が無く、
                オントロジー内の concept が単一の ``skos:inScheme`` を共有して
                いる場合はそれを使い、それ以外は ``metamesh_export``。

        Returns:
            書き込んだファイルへの絶対パス。
        """
        doc = _build(
            ontology_root=ontology_root,
            naming=naming,
            source_template=source_template,
            source_overrides=source_overrides,
            model_name_override=model_name_override,
        )
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
