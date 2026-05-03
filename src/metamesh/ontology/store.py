"""SKOS / OWL JSON-LD persistence for metamesh ontologies.

ファイル 1 つ = 概念または関係性 1 つ という単純な構成。Git 管理を想定。
保存前に rdflib で round-trip 検証して、壊れた JSON-LD は書かない。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from rdflib import Graph

BASE_NS = "https://metamesh.dev/ontology/"
EXT_NS = {
    "dv": "https://metamesh.dev/ext/dv/",
    "kimball": "https://metamesh.dev/ext/kimball/",
}

_BASE_CONTEXT: dict[str, Any] = {
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "@base": BASE_NS,
}

_SAFE_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def _validate_id(value: str, *, kind: str) -> None:
    if not value or "/" in value or value.startswith("."):
        raise ValueError(f"invalid {kind}: {value!r}")
    if not _SAFE_ID.match(value):
        raise ValueError(
            f"invalid {kind}: {value!r} (must match {_SAFE_ID.pattern})"
        )


class ConceptStore:
    """Store for both concepts (skos:Concept) and relationships (owl:ObjectProperty)."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.concepts_dir = root / "concepts"
        self.relationships_dir = root / "relationships"
        self.concepts_dir.mkdir(parents=True, exist_ok=True)
        self.relationships_dir.mkdir(parents=True, exist_ok=True)

    def save_concept(
        self,
        *,
        concept_id: str,
        pref_label_ja: str,
        definition_ja: str,
        pref_label_en: str | None,
        definition_en: str | None,
        alt_labels_ja: list[str],
        alt_labels_en: list[str],
        broader: str | None,
        narrower: list[str],
        related: list[str],
        scheme: str | None,
        extension: dict[str, Any] | list[dict[str, Any]] | None,
    ) -> Path:
        _validate_id(concept_id, kind="concept_id")

        doc = _build_jsonld(
            concept_id=concept_id,
            pref_label_ja=pref_label_ja,
            definition_ja=definition_ja,
            pref_label_en=pref_label_en,
            definition_en=definition_en,
            alt_labels_ja=alt_labels_ja,
            alt_labels_en=alt_labels_en,
            broader=broader,
            narrower=narrower,
            related=related,
            scheme=scheme,
            extension=extension,
        )

        # round-trip validation: parse via rdflib so we never persist broken JSON-LD
        g = Graph()
        g.parse(data=json.dumps(doc), format="json-ld")
        if len(g) == 0:
            raise ValueError("generated JSON-LD produced zero triples")

        path = self.concepts_dir / f"{concept_id}.jsonld"
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path

    def save_relationship(
        self,
        *,
        relationship_id: str,
        pref_label_ja: str,
        definition_ja: str,
        domain: str,
        range_: str,
        pref_label_en: str | None,
        definition_en: str | None,
        inverse_of: str | None,
        scheme: str | None,
        extension: dict[str, Any] | list[dict[str, Any]] | None,
    ) -> Path:
        _validate_id(relationship_id, kind="relationship_id")
        _validate_id(domain, kind="domain")
        _validate_id(range_, kind="range")
        if inverse_of is not None:
            _validate_id(inverse_of, kind="inverse_of")

        doc = _build_relationship_jsonld(
            relationship_id=relationship_id,
            pref_label_ja=pref_label_ja,
            definition_ja=definition_ja,
            domain=domain,
            range_=range_,
            pref_label_en=pref_label_en,
            definition_en=definition_en,
            inverse_of=inverse_of,
            scheme=scheme,
            extension=extension,
        )

        g = Graph()
        g.parse(data=json.dumps(doc), format="json-ld")
        if len(g) == 0:
            raise ValueError("generated JSON-LD produced zero triples")

        path = self.relationships_dir / f"{relationship_id}.jsonld"
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path


def _build_jsonld(
    *,
    concept_id: str,
    pref_label_ja: str,
    definition_ja: str,
    pref_label_en: str | None,
    definition_en: str | None,
    alt_labels_ja: list[str],
    alt_labels_en: list[str],
    broader: str | None,
    narrower: list[str],
    related: list[str],
    scheme: str | None,
    extension: dict[str, Any] | list[dict[str, Any]] | None,
) -> dict[str, Any]:
    context: dict[str, Any] = dict(_BASE_CONTEXT)

    pref_labels: list[dict[str, str]] = [{"@language": "ja", "@value": pref_label_ja}]
    if pref_label_en:
        pref_labels.append({"@language": "en", "@value": pref_label_en})

    definitions: list[dict[str, str]] = [{"@language": "ja", "@value": definition_ja}]
    if definition_en:
        definitions.append({"@language": "en", "@value": definition_en})

    alt_labels: list[dict[str, str]] = []
    alt_labels.extend({"@language": "ja", "@value": v} for v in alt_labels_ja)
    alt_labels.extend({"@language": "en", "@value": v} for v in alt_labels_en)

    doc: dict[str, Any] = {
        "@context": context,
        "@id": concept_id,
        "@type": "skos:Concept",
        "skos:prefLabel": pref_labels,
        "skos:definition": definitions,
    }
    if alt_labels:
        doc["skos:altLabel"] = alt_labels
    if broader:
        doc["skos:broader"] = {"@id": broader}
    if narrower:
        doc["skos:narrower"] = [{"@id": n} for n in narrower]
    if related:
        doc["skos:related"] = [{"@id": r} for r in related]
    if scheme:
        doc["skos:inScheme"] = {"@id": scheme}

    _apply_extensions(doc=doc, context=context, extension=extension)

    return doc


def _build_relationship_jsonld(
    *,
    relationship_id: str,
    pref_label_ja: str,
    definition_ja: str,
    domain: str,
    range_: str,
    pref_label_en: str | None,
    definition_en: str | None,
    inverse_of: str | None,
    scheme: str | None,
    extension: dict[str, Any] | list[dict[str, Any]] | None,
) -> dict[str, Any]:
    context: dict[str, Any] = dict(_BASE_CONTEXT)

    pref_labels: list[dict[str, str]] = [{"@language": "ja", "@value": pref_label_ja}]
    if pref_label_en:
        pref_labels.append({"@language": "en", "@value": pref_label_en})

    definitions: list[dict[str, str]] = [{"@language": "ja", "@value": definition_ja}]
    if definition_en:
        definitions.append({"@language": "en", "@value": definition_en})

    doc: dict[str, Any] = {
        "@context": context,
        "@id": relationship_id,
        "@type": "owl:ObjectProperty",
        "skos:prefLabel": pref_labels,
        "skos:definition": definitions,
        "rdfs:domain": {"@id": domain},
        "rdfs:range": {"@id": range_},
    }
    if inverse_of:
        doc["owl:inverseOf"] = {"@id": inverse_of}
    if scheme:
        doc["skos:inScheme"] = {"@id": scheme}

    _apply_extensions(doc=doc, context=context, extension=extension)

    return doc


def _normalize_extensions(
    extension: dict[str, Any] | list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Accept ``None`` / single dict / list of dicts and always return a list.

    Backward-compatible: existing callers passing a single dict
    (``extension={"namespace": "dv", "data": {...}}``) keep working.
    New callers can pass a list to attach multiple namespace extensions
    to the same document, which is what the Hybrid (DV + Kimball)
    Modeling Storming workflow needs.
    """
    if extension is None:
        return []
    if isinstance(extension, dict):
        return [extension]
    if isinstance(extension, list):
        return extension
    raise TypeError(
        f"extension must be dict, list[dict], or None; got {type(extension).__name__}"
    )


def _apply_extensions(
    *,
    doc: dict[str, Any],
    context: dict[str, Any],
    extension: dict[str, Any] | list[dict[str, Any]] | None,
) -> None:
    """Apply zero or more extensions to ``doc`` in order (later wins on conflicts).

    Each extension is ``{"namespace": str, "data": dict}``. Multiple
    extensions with the same namespace are valid; their ``data`` keys
    merge with last-wins semantics so the call site can build incremental
    overlays without needing prior knowledge of what's already there.
    """
    extensions = _normalize_extensions(extension)
    for ext in extensions:
        ns = ext.get("namespace")
        data = ext.get("data") or {}
        if ns not in EXT_NS:
            raise ValueError(
                f"unknown extension namespace: {ns!r}. registered: {sorted(EXT_NS)}"
            )
        context[ns] = EXT_NS[ns]
        for key, value in data.items():
            doc[f"{ns}:{key}"] = value
