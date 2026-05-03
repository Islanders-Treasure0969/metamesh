"""add_relationship MCP tool.

Claude が会話で集めた関係性 (NBR / OWL ObjectProperty) を JSON-LD として永続化する。
domain / range は事前に add_concept で登録済みの concept_id を想定。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from metamesh.ontology.store import ConceptStore


def register(mcp: FastMCP, *, ontology_root: Path) -> None:
    store = ConceptStore(ontology_root)

    @mcp.tool()
    def add_relationship(
        relationship_id: str,
        pref_label_ja: str,
        definition_ja: str,
        domain: str,
        range: str,
        pref_label_en: str | None = None,
        definition_en: str | None = None,
        inverse_of: str | None = None,
        scheme: str | None = None,
        extension: dict[str, Any] | list[dict[str, Any]] | None = None,
    ) -> str:
        """Register a business relationship (OWL ObjectProperty + SKOS metadata).

        Args:
            relationship_id: URI fragment (e.g. "owns_channel"). lower_snake_case 推奨。
            pref_label_ja: 日本語の優先名称 (skos:prefLabel @ja)。
            definition_ja: 日本語の定義文 (skos:definition @ja)。
            domain: 主語 (subject) 概念の concept_id (rdfs:domain)。
            range: 目的語 (object) 概念の concept_id (rdfs:range)。
            pref_label_en: 英語の優先名称。
            definition_en: 英語の定義文。
            inverse_of: 逆関係の relationship_id (owl:inverseOf)。
            scheme: 所属する skos:ConceptScheme の ID (例: "VTuberDomain")。
            extension: 方法論固有の拡張プロパティ。単一 namespace なら dict、
                複数 namespace 併記なら dict のリストを渡す
                (Hybrid DV+Kimball モデリングのユースケース向け)。
                例 (単一):
                    {"namespace": "dv",
                     "data": {"link": "LNK_STREAMER_CHANNEL", "cardinality": "1:N"}}
                例 (複数):
                    [{"namespace": "dv", "data": {"link": "LNK_COLLAB"}},
                     {"namespace": "kimball", "data": {"fact": "fct_collab"}}]

        Returns:
            保存先ファイルへのパス。
        """
        path = store.save_relationship(
            relationship_id=relationship_id,
            pref_label_ja=pref_label_ja,
            definition_ja=definition_ja,
            domain=domain,
            range_=range,
            pref_label_en=pref_label_en,
            definition_en=definition_en,
            inverse_of=inverse_of,
            scheme=scheme,
            extension=extension,
        )
        return f"Saved: {path}"
