"""Generate a Markdown digest of the ontology for AI/LLM prompt context.

Designed to be pasted (or read by a tool) into a Claude / GPT prompt so
the model can answer business questions with the right vocabulary,
synonyms, hierarchy, and DV/Kimball mappings of the domain.

Addresses PROJECT_CONTEXT.md §1.2 5th breakpoint (Data Catalog -> AI/LLM,
where ontological context is typically lost).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from metamesh.generators._common import (
    label_for_lang,
    load_jsonld_dir,
    split_alt_labels,
)


def export_llm_context(
    *,
    ontology_root: Path,
    title: str = "metamesh ontology context",
) -> str:
    """Build a Markdown digest of the ontology suitable for LLM prompt context.

    Args:
        ontology_root: Directory containing ``concepts/`` and ``relationships/``.
        title: H1 title rendered at the top of the document.

    Returns:
        UTF-8 Markdown text. Trailing newline included.
    """
    concepts = load_jsonld_dir(ontology_root / "concepts")
    relationships = load_jsonld_dir(ontology_root / "relationships")

    parts: list[str] = [
        f"# {title}",
        "",
        f"_Generated from `{ontology_root}` — "
        f"{len(concepts)} concepts, {len(relationships)} relationships._",
        "",
    ]

    if concepts:
        parts.append("## Concepts")
        parts.append("")
        parts.append(_concepts_summary_table(concepts))
        parts.append("")
        for c in concepts:
            parts.append(_concept_section(c))
            parts.append("")

    if relationships:
        parts.append("## Relationships")
        parts.append("")
        parts.append(_relationships_summary_table(relationships))
        parts.append("")
        for r in relationships:
            parts.append(_relationship_section(r))
            parts.append("")

    return "\n".join(parts).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Summary tables
# ---------------------------------------------------------------------------


def _concepts_summary_table(concepts: list[dict[str, Any]]) -> str:
    rows = [
        "| ID | Label (ja) | Label (en) | DV |",
        "|---|---|---|---|",
    ]
    for c in concepts:
        cid = c["@id"]
        ja = label_for_lang(c.get("skos:prefLabel"), "ja") or ""
        en = label_for_lang(c.get("skos:prefLabel"), "en") or ""
        hub = c.get("dv:hub") or c.get("dv:link") or ""
        rows.append(f"| `{cid}` | {ja} | {en} | {hub} |")
    return "\n".join(rows)


def _relationships_summary_table(relationships: list[dict[str, Any]]) -> str:
    rows = [
        "| ID | Label (ja) | Domain | Range | Cardinality | DV Link |",
        "|---|---|---|---|---|---|",
    ]
    for r in relationships:
        rid = r["@id"]
        ja = label_for_lang(r.get("skos:prefLabel"), "ja") or ""
        domain = (r.get("rdfs:domain") or {}).get("@id", "")
        range_ = (r.get("rdfs:range") or {}).get("@id", "")
        card = r.get("dv:cardinality", "")
        link = r.get("dv:link", "")
        rows.append(f"| `{rid}` | {ja} | `{domain}` | `{range_}` | {card} | {link} |")
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# Per-document detail sections
# ---------------------------------------------------------------------------


def _concept_section(concept: dict[str, Any]) -> str:
    cid = concept["@id"]
    ja = label_for_lang(concept.get("skos:prefLabel"), "ja") or cid
    en = label_for_lang(concept.get("skos:prefLabel"), "en")
    def_ja = label_for_lang(concept.get("skos:definition"), "ja")
    def_en = label_for_lang(concept.get("skos:definition"), "en")
    alt_ja, alt_en = split_alt_labels(concept.get("skos:altLabel"))

    heading = f"### `{cid}` — {ja}" + (f" / {en}" if en else "")
    lines: list[str] = [heading, ""]
    if def_ja:
        lines += [def_ja, ""]
    if def_en:
        lines += [f"_{def_en}_", ""]

    if alt_ja or alt_en:
        lines.append("**Synonyms:**")
        if alt_ja:
            lines.append(f"- ja: {', '.join(alt_ja)}")
        if alt_en:
            lines.append(f"- en: {', '.join(alt_en)}")
        lines.append("")

    rel_lines: list[str] = []
    if "skos:broader" in concept:
        rel_lines.append(f"- broader: `{concept['skos:broader']['@id']}`")
    narrower = concept.get("skos:narrower")
    if narrower:
        items = ", ".join(f"`{n['@id']}`" for n in narrower)
        rel_lines.append(f"- narrower: {items}")
    related = concept.get("skos:related")
    if related:
        items = ", ".join(f"`{r['@id']}`" for r in related)
        rel_lines.append(f"- related: {items}")
    if rel_lines:
        lines.append("**Ontology links:**")
        lines.extend(rel_lines)
        lines.append("")

    lines.extend(_extension_block(concept, "dv", "DV implementation"))
    lines.extend(_extension_block(concept, "kimball", "Kimball implementation"))

    if "skos:inScheme" in concept:
        lines.append(f"_Scheme: `{concept['skos:inScheme']['@id']}`_")

    return "\n".join(lines).rstrip()


def _relationship_section(rel: dict[str, Any]) -> str:
    rid = rel["@id"]
    ja = label_for_lang(rel.get("skos:prefLabel"), "ja") or rid
    en = label_for_lang(rel.get("skos:prefLabel"), "en")
    def_ja = label_for_lang(rel.get("skos:definition"), "ja")
    def_en = label_for_lang(rel.get("skos:definition"), "en")
    domain = (rel.get("rdfs:domain") or {}).get("@id", "?")
    range_ = (rel.get("rdfs:range") or {}).get("@id", "?")
    cardinality = rel.get("dv:cardinality")

    heading = f"### `{rid}` — {ja}" + (f" / {en}" if en else "")
    arrow = f"`{domain}` → `{range_}`" + (f"  ({cardinality})" if cardinality else "")

    lines: list[str] = [heading, "", arrow, ""]
    if def_ja:
        lines += [def_ja, ""]
    if def_en:
        lines += [f"_{def_en}_", ""]

    if "owl:inverseOf" in rel:
        lines += [f"**Inverse of:** `{rel['owl:inverseOf']['@id']}`", ""]

    lines.extend(_extension_block(rel, "dv", "DV implementation"))
    lines.extend(_extension_block(rel, "kimball", "Kimball implementation"))

    if "skos:inScheme" in rel:
        lines.append(f"_Scheme: `{rel['skos:inScheme']['@id']}`_")

    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extension_block(doc: dict[str, Any], ns: str, header: str) -> list[str]:
    prefix = f"{ns}:"
    data = {k[len(prefix):]: v for k, v in doc.items() if k.startswith(prefix)}
    if not data:
        return []
    out: list[str] = [f"**{header}:**"]
    for k, v in data.items():
        out.append(f"- `{k}`: {_format_value(v)}")
    out.append("")
    return out


def _format_value(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)
