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


def sparql_query(
    *,
    ontology_root: Path,
    sparql: str,
    limit: int = 100,
) -> dict[str, Any]:
    """Run a SPARQL query against the merged ontology graph.

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
