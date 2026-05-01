"""export_llm_context MCP tool.

Reads the metamesh ontology and writes a Markdown digest that can be pasted
(or read by another tool) into an LLM prompt to give the model the business
vocabulary, synonyms, hierarchy, and DV/Kimball implementation hints of the
domain it's reasoning about.
"""
from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from metamesh.generators.llm_context import export_llm_context as _build


def register(mcp: FastMCP, *, ontology_root: Path) -> None:
    @mcp.tool()
    def export_llm_context(
        output_path: str,
        title: str = "metamesh ontology context",
    ) -> str:
        """Export the ontology as a Markdown digest for LLM prompt context.

        Args:
            output_path: 出力先パス。親ディレクトリが無ければ作成する。
            title: H1 として使われるドキュメントタイトル。デフォルトは
                ``"metamesh ontology context"``。

        Returns:
            書き込んだファイルへの絶対パス。
        """
        text = _build(ontology_root=ontology_root, title=title)
        out = Path(output_path).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        return f"Wrote: {out}"
