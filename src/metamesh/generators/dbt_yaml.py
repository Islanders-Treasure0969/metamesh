"""Generate a dbt schema.yml fragment from a metamesh ontology directory.

Pure function over ontology files - no MCP / FastMCP dependency.
The MCP tool wrapper lives in metamesh.tools.generate_dbt_yaml.

Output shape:
    {"version": 2, "models": [{name, description, meta}, ...]}

Each ontology Concept and Relationship becomes one entry under `models:`.
The original ontology @id is always preserved in `meta.ontology_id`, so the
generated YAML can be merged into an existing dbt project without losing
the link back to the SSoT.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from metamesh.generators._common import (
    attach_extension_meta,
    label_for_lang,
    load_jsonld_dir,
    model_name,
    split_alt_labels,
    validate_naming,
)


def generate_dbt_yaml(
    *,
    ontology_root: Path,
    naming: str = "dv_lower",
) -> dict[str, Any]:
    """Build the dbt schema.yml dict for a given ontology root.

    Args:
        ontology_root: Directory containing ``concepts/`` and ``relationships/``.
        naming: Model naming strategy.
            - ``"as_is"``: use the @id verbatim (e.g. ``Streamer``)
            - ``"dv_lower"`` (default): lowercase ``dv:hub`` / ``dv:link`` if
              present (e.g. ``hub_streamer``); fallback to snake_case(@id)
            - ``"snake"``: always snake_case the @id (e.g. ``streamer``)
    """
    validate_naming(naming)

    concepts = load_jsonld_dir(ontology_root / "concepts")
    relationships = load_jsonld_dir(ontology_root / "relationships")

    models: list[dict[str, Any]] = []
    for c in concepts:
        models.append(_concept_to_model(c, naming=naming))
    for r in relationships:
        models.append(_relationship_to_model(r, naming=naming))

    _detect_name_collisions(models)
    return {"version": 2, "models": models}


def _detect_name_collisions(models: list[dict[str, Any]]) -> None:
    """Raise if two ontology elements collapse to the same dbt model name.

    Most often this means a Concept and a Relationship are both pointing at
    the same DV link (e.g. ``Collaboration`` concept and ``participates_in``
    relationship both carry ``dv:link: LNK_COLLAB``). The fix is at the
    ontology level: keep DV link metadata on exactly one of them.
    """
    seen: dict[str, list[str]] = {}
    for m in models:
        seen.setdefault(m["name"], []).append(
            f"{m['meta']['ontology_type']} '{m['meta']['ontology_id']}'"
        )
    collisions = {name: srcs for name, srcs in seen.items() if len(srcs) > 1}
    if collisions:
        details = "; ".join(
            f"{name} <- {' + '.join(srcs)}" for name, srcs in sorted(collisions.items())
        )
        raise ValueError(
            "duplicate dbt model name(s) generated from ontology: "
            f"{details}. Resolve at the ontology level (typically: keep DV "
            "extension metadata on exactly one of Concept vs Relationship)."
        )


# ---------------------------------------------------------------------------
# Per-document transforms
# ---------------------------------------------------------------------------


def _concept_to_model(concept: dict[str, Any], *, naming: str) -> dict[str, Any]:
    return {
        "name": model_name(concept, oid=concept["@id"], naming=naming),
        "description": _build_concept_description(concept),
        "meta": _build_concept_meta(concept),
    }


def _relationship_to_model(rel: dict[str, Any], *, naming: str) -> dict[str, Any]:
    return {
        "name": model_name(rel, oid=rel["@id"], naming=naming),
        "description": _build_relationship_description(rel),
        "meta": _build_relationship_meta(rel),
    }


# ---------------------------------------------------------------------------
# Description builders
# ---------------------------------------------------------------------------


def _build_concept_description(concept: dict[str, Any]) -> str:
    pref_ja = label_for_lang(concept.get("skos:prefLabel"), "ja")
    pref_en = label_for_lang(concept.get("skos:prefLabel"), "en")
    def_ja = label_for_lang(concept.get("skos:definition"), "ja")
    def_en = label_for_lang(concept.get("skos:definition"), "en")

    alt_ja, alt_en = split_alt_labels(concept.get("skos:altLabel"))

    title = pref_ja or concept["@id"]
    if pref_en and pref_en != title:
        title = f"{title} ({pref_en})"

    lines = [f"# {title}"]
    if def_ja:
        lines += ["", def_ja]
    if def_en:
        lines += ["", def_en]
    if alt_ja or alt_en:
        lines += ["", "## Synonyms"]
        if alt_ja:
            lines.append(f"- ja: {', '.join(alt_ja)}")
        if alt_en:
            lines.append(f"- en: {', '.join(alt_en)}")
    return "\n".join(lines)


def _build_relationship_description(rel: dict[str, Any]) -> str:
    pref_ja = label_for_lang(rel.get("skos:prefLabel"), "ja")
    pref_en = label_for_lang(rel.get("skos:prefLabel"), "en")
    def_ja = label_for_lang(rel.get("skos:definition"), "ja")
    def_en = label_for_lang(rel.get("skos:definition"), "en")
    domain = (rel.get("rdfs:domain") or {}).get("@id")
    range_ = (rel.get("rdfs:range") or {}).get("@id")
    cardinality = rel.get("dv:cardinality")

    title = pref_ja or rel["@id"]
    if pref_en and pref_en != title:
        title = f"{title} ({pref_en})"

    lines = [f"# {title}"]
    if domain and range_:
        arrow = f"`{domain}` → `{range_}`"
        if cardinality:
            arrow = f"{arrow}  ({cardinality})"
        lines += ["", arrow]
    if def_ja:
        lines += ["", def_ja]
    if def_en:
        lines += ["", def_en]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Meta builders
# ---------------------------------------------------------------------------


def _build_concept_meta(concept: dict[str, Any]) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "ontology_id": concept["@id"],
        "ontology_type": "concept",
    }
    if "skos:inScheme" in concept:
        meta["ontology_scheme"] = concept["skos:inScheme"]["@id"]
    if "skos:broader" in concept:
        meta["ontology_broader"] = concept["skos:broader"]["@id"]
    narrower = concept.get("skos:narrower")
    if narrower:
        meta["ontology_narrower"] = [n["@id"] for n in narrower]
    related = concept.get("skos:related")
    if related:
        meta["ontology_related"] = [r["@id"] for r in related]

    attach_extension_meta(doc=concept, meta=meta)
    return meta


def _build_relationship_meta(rel: dict[str, Any]) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "ontology_id": rel["@id"],
        "ontology_type": "relationship",
        "ontology_domain": (rel.get("rdfs:domain") or {}).get("@id"),
        "ontology_range": (rel.get("rdfs:range") or {}).get("@id"),
    }
    if "owl:inverseOf" in rel:
        meta["ontology_inverse_of"] = rel["owl:inverseOf"]["@id"]
    if "skos:inScheme" in rel:
        meta["ontology_scheme"] = rel["skos:inScheme"]["@id"]

    attach_extension_meta(doc=rel, meta=meta)
    return meta
