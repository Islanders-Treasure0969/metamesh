"""SKOS JSON-LD persistence for metamesh concepts.

ファイル 1 つ = 概念 1 つ という単純な構成。Git 管理を想定。
保存前に rdflib で round-trip 検証して、壊れた JSON-LD は書かない。
"""
from __future__ import annotations

import json
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


class ConceptStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.concepts_dir = root / "concepts"
        self.concepts_dir.mkdir(parents=True, exist_ok=True)

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
        extension: dict[str, Any] | None,
    ) -> Path:
        if not concept_id or "/" in concept_id or concept_id.startswith("."):
            raise ValueError(f"invalid concept_id: {concept_id!r}")

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
    extension: dict[str, Any] | None,
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

    if extension:
        ns = extension.get("namespace")
        data = extension.get("data") or {}
        if ns not in EXT_NS:
            raise ValueError(
                f"unknown extension namespace: {ns!r}. registered: {sorted(EXT_NS)}"
            )
        context[ns] = EXT_NS[ns]
        for key, value in data.items():
            doc[f"{ns}:{key}"] = value

    return doc
