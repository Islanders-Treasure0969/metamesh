"""Generate a dbt MetricFlow semantic-layer YAML fragment from an ontology.

Pure function over ontology files (no MCP dependency). The MCP tool wrapper
lives in metamesh.tools.generate_semantic_layer.

Output shape (subset of the MetricFlow spec):
    {
        "semantic_models": [
            {name, description, model, entities, dimensions, measures},
            ...
        ],
        "metrics": [],
    }

Mapping rules:

- A Concept that carries ``dv:hub`` becomes a semantic_model whose primary
  entity is the concept itself (``expr`` = the concept's
  ``dv:business_key``). Concepts without a DV hub (pure SKOS notions like
  Collaboration) are skipped because they have no physical table to bind.

- A Relationship that carries ``dv:link`` becomes a semantic_model whose
  foreign entities are the ``rdfs:domain`` and ``rdfs:range`` concepts.
  Each foreign entity's ``expr`` is taken from the related concept's
  ``dv:business_key`` so MetricFlow can join the link table back to its
  hubs without extra configuration.

Metrics are not emitted: the current ontology vocabulary doesn't model
them yet (a future ``add_metric`` tool will). The empty list is kept so
the output is a valid, mergeable MetricFlow document.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from metamesh.generators._common import (
    label_for_lang,
    load_jsonld_dir,
    model_name,
    snake,
    validate_naming,
)


def generate_semantic_layer(
    *,
    ontology_root: Path,
    naming: str = "dv_lower",
) -> dict[str, Any]:
    """Build the MetricFlow semantic_layer dict for a given ontology root.

    Args:
        ontology_root: Directory containing ``concepts/`` and ``relationships/``.
        naming: Model naming strategy (same options as ``generate_dbt_yaml``).

    Returns:
        ``{"semantic_models": [...], "metrics": []}``
    """
    validate_naming(naming)

    concepts = load_jsonld_dir(ontology_root / "concepts")
    relationships = load_jsonld_dir(ontology_root / "relationships")
    concept_index = {c["@id"]: c for c in concepts}

    semantic_models: list[dict[str, Any]] = []
    for c in concepts:
        sm = _concept_to_semantic_model(c, naming=naming)
        if sm is not None:
            semantic_models.append(sm)
    for r in relationships:
        sm = _relationship_to_semantic_model(
            r, naming=naming, concept_index=concept_index
        )
        if sm is not None:
            semantic_models.append(sm)

    _detect_name_collisions(semantic_models)
    return {"semantic_models": semantic_models, "metrics": []}


def _detect_name_collisions(semantic_models: list[dict[str, Any]]) -> None:
    seen: dict[str, int] = {}
    for sm in semantic_models:
        seen[sm["name"]] = seen.get(sm["name"], 0) + 1
    dupes = [name for name, n in seen.items() if n > 1]
    if dupes:
        raise ValueError(
            "duplicate semantic_model name(s): "
            f"{sorted(dupes)}. Resolve at the ontology level "
            "(typically: keep DV extension metadata on exactly one of "
            "Concept vs Relationship)."
        )


# ---------------------------------------------------------------------------
# Per-document transforms
# ---------------------------------------------------------------------------


def _concept_to_semantic_model(
    concept: dict[str, Any], *, naming: str
) -> dict[str, Any] | None:
    hub = concept.get("dv:hub")
    if not isinstance(hub, str) or not hub:
        # Skip concepts that don't bind to a physical Hub table.
        return None

    cid = concept["@id"]
    name = model_name(concept, oid=cid, naming=naming)
    business_key = concept.get("dv:business_key") or _fallback_key(cid)

    return {
        "name": name,
        "description": _short_description(concept),
        "model": f"ref('{name}')",
        "entities": [
            {
                "name": snake(cid),
                "type": "primary",
                "expr": business_key,
            }
        ],
        "dimensions": [],
        "measures": [],
    }


def _relationship_to_semantic_model(
    rel: dict[str, Any],
    *,
    naming: str,
    concept_index: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    link = rel.get("dv:link")
    if not isinstance(link, str) or not link:
        return None

    rid = rel["@id"]
    name = model_name(rel, oid=rid, naming=naming)

    domain_id = (rel.get("rdfs:domain") or {}).get("@id")
    range_id = (rel.get("rdfs:range") or {}).get("@id")

    entities: list[dict[str, Any]] = []
    seen_entity_names: set[str] = set()
    for cid in (domain_id, range_id):
        if not cid:
            continue
        ent_name = snake(cid)
        if ent_name in seen_entity_names:
            # Self-link (Streamer x Streamer etc.): suffix to avoid duplicate names.
            ent_name = f"{ent_name}_other"
        seen_entity_names.add(ent_name)
        related_concept = concept_index.get(cid, {})
        bk = related_concept.get("dv:business_key") or _fallback_key(cid)
        entities.append(
            {
                "name": ent_name,
                "type": "foreign",
                "expr": bk,
            }
        )

    return {
        "name": name,
        "description": _short_description(rel),
        "model": f"ref('{name}')",
        "entities": entities,
        "dimensions": [],
        "measures": [],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _short_description(doc: dict[str, Any]) -> str:
    """One-line description = pref label (ja/en) + first sentence of definition."""
    pref_ja = label_for_lang(doc.get("skos:prefLabel"), "ja")
    pref_en = label_for_lang(doc.get("skos:prefLabel"), "en")
    def_ja = label_for_lang(doc.get("skos:definition"), "ja") or ""

    title = pref_ja or doc["@id"]
    if pref_en and pref_en != title:
        title = f"{title} ({pref_en})"

    # MetricFlow descriptions are typically one paragraph; keep it concise.
    short_def = def_ja.split("。")[0].strip()
    if short_def and not short_def.endswith("。"):
        short_def += "。"
    return f"{title}: {short_def}" if short_def else title


def _fallback_key(concept_id: str) -> str:
    """Best-effort guess when a related concept lacks ``dv:business_key``."""
    return f"{snake(concept_id)}_id"
