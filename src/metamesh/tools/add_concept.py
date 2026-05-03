"""add_concept MCP tool.

Claude が会話でインタビューして集めた概念情報を SKOS JSON-LD として永続化する。
1 回のツール呼び出しで完結する想定（インタビュー自体はチャット側で行う）。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from metamesh.ontology.store import ConceptStore


def register(mcp: FastMCP, *, ontology_root: Path) -> None:
    store = ConceptStore(ontology_root)

    @mcp.tool()
    def add_concept(
        concept_id: str,
        pref_label_ja: str,
        definition_ja: str,
        pref_label_en: str | None = None,
        definition_en: str | None = None,
        alt_labels_ja: list[str] | None = None,
        alt_labels_en: list[str] | None = None,
        broader: str | None = None,
        narrower: list[str] | None = None,
        related: list[str] | None = None,
        scheme: str | None = None,
        extension: dict[str, Any] | list[dict[str, Any]] | None = None,
    ) -> str:
        """Register a business concept as SKOS JSON-LD.

        Args:
            concept_id: URI fragment (e.g. "Streamer"). PascalCase 推奨。
            pref_label_ja: 日本語の優先名称 (skos:prefLabel @ja)。
            definition_ja: 日本語の定義文 (skos:definition @ja)。
            pref_label_en: 英語の優先名称。
            definition_en: 英語の定義文。
            alt_labels_ja: 日本語の同義語 (skos:altLabel @ja)。
            alt_labels_en: 英語の同義語 (skos:altLabel @en)。
            broader: 上位概念の concept_id (skos:broader)。
            narrower: 下位概念の concept_id 群 (skos:narrower)。
            related: 関連概念の concept_id 群 (skos:related)。
            scheme: 所属する skos:ConceptScheme の ID (例: "VTuberDomain")。
            extension: 方法論固有の拡張プロパティ。単一 namespace なら dict、
                複数 namespace を併記するなら dict のリストを渡す
                (Hybrid DV+Kimball モデリングのユースケース向け)。
                例 (単一):
                    {"namespace": "dv", "data": {"hub": "HUB_STREAMER"}}
                例 (複数):
                    [{"namespace": "dv", "data": {"hub": "HUB_STREAMER"}},
                     {"namespace": "kimball", "data": {"dimension": "dim_streamer", "scd_type": 2}}]

        Returns:
            保存先ファイルへのパス。
        """
        path = store.save_concept(
            concept_id=concept_id,
            pref_label_ja=pref_label_ja,
            definition_ja=definition_ja,
            pref_label_en=pref_label_en,
            definition_en=definition_en,
            alt_labels_ja=alt_labels_ja or [],
            alt_labels_en=alt_labels_en or [],
            broader=broader,
            narrower=narrower or [],
            related=related or [],
            scheme=scheme,
            extension=extension,
        )
        return f"Saved: {path}"
