"""query_concept MCP tool.

Search the metamesh ontology either by keyword (substring across labels /
definitions / ids) or by SPARQL (structured query against the merged graph).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from metamesh.queries.concept import keyword_search, sparql_query


def register(mcp: FastMCP, *, ontology_root: Path) -> None:
    @mcp.tool()
    def query_concept(
        keyword: str | None = None,
        sparql: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Search the ontology by keyword or SPARQL.

        Exactly one of ``keyword`` or ``sparql`` must be provided.

        Args:
            keyword: 部分一致検索する文字列 (case-insensitive)。
                ``@id`` / ``skos:prefLabel`` (ja, en) / ``skos:altLabel``
                (ja, en) / ``skos:definition`` (ja, en) を走査する。
                マッチした field 群と該当 value の snippet を返す。
            sparql: 生 SPARQL クエリ (SELECT 推奨)。merged ontology graph
                (concepts + relationships) に対して実行する。
            limit: 返す最大件数 (default 20)。

        Returns:
            keyword モード:
                ``{"mode": "keyword", "keyword", "matches": [...],
                   "count", "truncated"}``
            sparql モード:
                ``{"mode": "sparql", "sparql", "columns", "rows": [...],
                   "count", "truncated"}``
        """
        if (keyword is None) == (sparql is None):
            raise ValueError(
                "Exactly one of `keyword` or `sparql` must be provided "
                "(both given or both omitted)."
            )
        if keyword is not None:
            return keyword_search(
                ontology_root=ontology_root, keyword=keyword, limit=limit
            )
        assert sparql is not None  # for type checker
        return sparql_query(
            ontology_root=ontology_root, sparql=sparql, limit=limit
        )
