"""Read-side query functions for the metamesh ontology.

Two modes:

- ``keyword_search``: case-insensitive substring match across
  @id / skos:prefLabel / skos:altLabel / skos:definition. Designed for
  end-user discovery ("does the ontology already have a concept for...").

- ``sparql_query``: arbitrary SPARQL SELECT against the merged ontology
  graph. Designed for structured queries (e.g. "all hubs",
  "all relationships with cardinality 1:N", graph traversal).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from rdflib import Graph

from metamesh.generators._common import (
    label_for_lang,
    load_jsonld_dir,
    split_alt_labels,
)


# ---------------------------------------------------------------------------
# Keyword search
# ---------------------------------------------------------------------------


def keyword_search(
    *,
    ontology_root: Path,
    keyword: str,
    limit: int = 20,
) -> dict[str, Any]:
    """Substring search across labels, definitions, and identifiers.

    Returns one entry per matched document, even if multiple fields match
    (the matched fields are aggregated into ``matched_fields``).
    """
    if not keyword:
        raise ValueError("keyword must be a non-empty string")

    needle = keyword.lower()
    concepts = load_jsonld_dir(ontology_root / "concepts")
    relationships = load_jsonld_dir(ontology_root / "relationships")

    matches: list[dict[str, Any]] = []
    truncated = False
    for doc, doc_type in (
        *((c, "concept") for c in concepts),
        *((r, "relationship") for r in relationships),
    ):
        entry = _match_doc(doc, doc_type, needle)
        if entry is None:
            continue
        if len(matches) >= limit:
            truncated = True
            break
        matches.append(entry)

    return {
        "mode": "keyword",
        "keyword": keyword,
        "matches": matches,
        "count": len(matches),
        "truncated": truncated,
    }


def _match_doc(
    doc: dict[str, Any], doc_type: str, needle: str
) -> dict[str, Any] | None:
    """Return one match entry if any field contains the needle, else None."""
    oid = doc["@id"]
    pref_ja = label_for_lang(doc.get("skos:prefLabel"), "ja") or ""
    pref_en = label_for_lang(doc.get("skos:prefLabel"), "en") or ""
    def_ja = label_for_lang(doc.get("skos:definition"), "ja") or ""
    def_en = label_for_lang(doc.get("skos:definition"), "en") or ""
    alt_ja, alt_en = split_alt_labels(doc.get("skos:altLabel"))

    matched_fields: list[dict[str, str]] = []
    if needle in oid.lower():
        matched_fields.append({"field": "@id", "value": oid})
    if needle in pref_ja.lower():
        matched_fields.append({"field": "skos:prefLabel@ja", "value": pref_ja})
    if needle in pref_en.lower():
        matched_fields.append({"field": "skos:prefLabel@en", "value": pref_en})
    for v in alt_ja:
        if needle in v.lower():
            matched_fields.append({"field": "skos:altLabel@ja", "value": v})
    for v in alt_en:
        if needle in v.lower():
            matched_fields.append({"field": "skos:altLabel@en", "value": v})
    if needle in def_ja.lower():
        matched_fields.append(
            {"field": "skos:definition@ja", "value": _snippet(def_ja, needle)}
        )
    if needle in def_en.lower():
        matched_fields.append(
            {"field": "skos:definition@en", "value": _snippet(def_en, needle)}
        )

    if not matched_fields:
        return None

    return {
        "id": oid,
        "type": doc_type,
        "pref_label_ja": pref_ja or None,
        "pref_label_en": pref_en or None,
        "matched_fields": matched_fields,
    }


def _snippet(text: str, needle: str, context: int = 60) -> str:
    """Extract a snippet of ``text`` centered around the first ``needle`` hit."""
    idx = text.lower().find(needle)
    if idx < 0:
        return text[: context * 2]
    start = max(0, idx - context)
    end = min(len(text), idx + len(needle) + context)
    snippet = text[start:end]
    if start > 0:
        snippet = "…" + snippet
    if end < len(text):
        snippet = snippet + "…"
    return snippet


# ---------------------------------------------------------------------------
# SPARQL
# ---------------------------------------------------------------------------


# SPARQL Update キーワード (W3C SPARQL 1.1 Update 仕様より)。
# query_concept は SKILL.md / docstring で read-only を契約しているため、
# Update 系を実装層で物理的にブロックする (in-memory rdflib Graph に対する
# 一時的なミューテーションでも、契約と挙動の乖離を避ける)。
_FORBIDDEN_SPARQL_UPDATE_RE = re.compile(
    r"\b(INSERT|DELETE|DROP|LOAD|CLEAR|CREATE|COPY|MOVE|ADD|MODIFY|WITH)\b",
    re.IGNORECASE,
)


def _strip_sparql_literals_and_comments(sparql: str) -> str:
    """文字列リテラル・IRI 参照・コメントを潰す (キーワード検出の false positive 抑止)。

    例: ``"INSERT がリテラル内にある"`` や IRI 内の ``#`` を Update と誤検知
    させない。厳密な SPARQL パーサではないが、Update キーワードが識別子
    位置で出てくるパターンを実用上カバーする。

    **順序が重要**: コメント除去 (``#[^\\n]*``) を最初にやると、IRI
    ``<http://.../core#>`` の ``#`` 以降が消えて、同一行の後続トークン
    (``INSERT`` 等) も巻き込まれる。これは read-only バリデーションの
    バイパスになる (`PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    INSERT DATA { ... }` が "PREFIX skos: <http://www.w3.org/2004/02/skos/core"
    として通る)。

    そのため: 文字列リテラル → IRI 参照 → コメントの順で中和する。
    """
    # (1) 文字列リテラル (triple-quoted は先に、長い順)
    cleaned = re.sub(r'""".*?"""', '""', sparql, flags=re.DOTALL)
    cleaned = re.sub(r"'''.*?'''", "''", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'"[^"\n\\]*(?:\\.[^"\n\\]*)*"', '""', cleaned)
    cleaned = re.sub(r"'[^'\n\\]*(?:\\.[^'\n\\]*)*'", "''", cleaned)
    # (2) IRI 参照 (`#` を含みうる; コメント除去より前に潰す)
    cleaned = re.sub(r"<[^>\n]*>", "<>", cleaned)
    # (3) コメント (# から行末) — IRI 中和後なので安全
    cleaned = re.sub(r"#[^\n]*", "", cleaned)
    return cleaned


def _validate_read_only_sparql(sparql: str) -> None:
    """SPARQL Update (INSERT/DELETE/DROP 等) を拒否する。

    query_concept は SELECT / CONSTRUCT / DESCRIBE / ASK のみサポートする
    契約。違反した場合は ValueError を投げて graph に届く前に止める。
    """
    cleaned = _strip_sparql_literals_and_comments(sparql)
    match = _FORBIDDEN_SPARQL_UPDATE_RE.search(cleaned)
    if match:
        raise ValueError(
            f"SPARQL Update keyword '{match.group(0).upper()}' is not allowed. "
            "query_concept is read-only; use SELECT / CONSTRUCT / DESCRIBE / ASK "
            "only."
        )


def sparql_query(
    *,
    ontology_root: Path,
    sparql: str,
    limit: int = 100,
) -> dict[str, Any]:
    """Run a SPARQL query against the merged ontology graph.

    **Read-only**: SPARQL Update (INSERT / DELETE / DROP / LOAD / CLEAR /
    CREATE / COPY / MOVE / ADD / MODIFY / WITH) は実装層で拒否する。
    metamesh は in-memory graph を毎回再構築するためミューテーションは
    JSON-LD ファイルに永続化されないが、Skill 契約 (read-only) と挙動の
    乖離を避けるため明示的にバリデートする。

    Auto-detects the query form and shapes the response accordingly:

    - ``SELECT`` -> ``{type: "SELECT", columns, rows, count, truncated}``
    - ``CONSTRUCT`` / ``DESCRIBE`` -> ``{type, triples: [[s, p, o], ...],
      count, truncated}``. Useful for Skills that want a subgraph
      (e.g. "all triples around Streamer") to render as Mermaid /
      networkx / Cytoscape on the client side.
    - ``ASK`` -> ``{type: "ASK", boolean}``
    """
    if not sparql or not sparql.strip():
        raise ValueError("sparql must be a non-empty string")
    _validate_read_only_sparql(sparql)

    graph = _load_full_graph(ontology_root)

    qres = graph.query(sparql)
    qtype = qres.type  # "SELECT" | "CONSTRUCT" | "DESCRIBE" | "ASK"

    if qtype == "SELECT":
        columns = [str(v) for v in (qres.vars or [])]
        rows: list[list[str | None]] = []
        truncated = False
        for row in qres:
            if len(rows) >= limit:
                truncated = True
                break
            rows.append([_format_term(t) for t in row])
        return {
            "mode": "sparql",
            "type": "SELECT",
            "sparql": sparql,
            "columns": columns,
            "rows": rows,
            "count": len(rows),
            "truncated": truncated,
        }

    if qtype in ("CONSTRUCT", "DESCRIBE"):
        triples: list[list[str | None]] = []
        truncated = False
        for s, p, o in qres:
            if len(triples) >= limit:
                truncated = True
                break
            triples.append([_format_term(s), _format_term(p), _format_term(o)])
        return {
            "mode": "sparql",
            "type": qtype,
            "sparql": sparql,
            "triples": triples,
            "count": len(triples),
            "truncated": truncated,
        }

    if qtype == "ASK":
        return {
            "mode": "sparql",
            "type": "ASK",
            "sparql": sparql,
            "boolean": bool(qres),
        }

    raise ValueError(f"unsupported SPARQL query type: {qtype!r}")


def _load_full_graph(ontology_root: Path) -> Graph:
    g = Graph()
    for d in ("concepts", "relationships"):
        path = ontology_root / d
        if not path.exists():
            continue
        for p in sorted(path.glob("*.jsonld")):
            g.parse(p, format="json-ld")
    return g


def _format_term(term: Any) -> str | None:
    if term is None:
        return None
    return str(term)
