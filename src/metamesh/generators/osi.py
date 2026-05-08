"""Generate an OSI (Open Semantic Interchange) YAML fragment from an ontology.

OSI v0.1.1 (公式アナウンスは v1.0 系) は Snowflake / dbt Labs / Salesforce /
Databricks 主導の vendor-neutral な semantic layer 交換フォーマット
(Apache 2.0)。詳細仕様は https://github.com/open-semantic-interchange/OSI

Pure function over ontology files (no MCP dependency)。
The MCP tool wrapper lives in metamesh.tools.generate_osi_yaml.

Output shape (subset of the OSI core-spec):
    {
        "version": "0.1.1",
        "semantic_model": [
            {
                "name": <scheme or "metamesh_export">,
                "datasets": [...],
                "relationships": [...],
                "metrics": [],
            }
        ],
    }

Mapping rules:

- A Concept that carries ``dv:hub`` becomes an OSI ``Dataset``。Concepts
  without a DV hub (pure SKOS notions like Collaboration) are skipped
  because they have no physical table to bind.

- A Relationship that carries ``dv:link`` becomes an OSI ``Relationship``。
  ``dv:cardinality`` を尊重し、OSI の慣習 (``from`` = many-side、``to`` =
  one-side) に合わせて、``1:N`` の場合は range が many-side として ``from``
  に入る。``N:M`` は OSI に直接対応概念がないため skip して warn する。

- ``Dataset.source`` は OSI で必須だが metamesh のオントロジーは logical
  only なので、``source_template`` (default: ``LOGICAL.{name}``) で
  プレースホルダを埋める。実際の ``database.schema.table`` には
  ``source_overrides`` で個別差し替え、または出力後に手動編集する。

- 多言語ラベル (``skos:altLabel``) は ``Dataset.ai_context.synonyms`` へ
  flatten (ja + en を結合)。``skos:definition`` は
  ``Dataset.ai_context.instructions`` へ。

- DV / Kimball 拡張は失わないように ``Dataset.custom_extensions`` の
  ``vendor_name: COMMON`` で JSON 文字列として保持する。
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from metamesh.generators._common import (
    EXT_NAMESPACES,
    label_for_lang,
    load_jsonld_dir,
    model_name,
    snake,
    validate_naming,
)

logger = logging.getLogger(__name__)

OSI_VERSION = "0.1.1"
DEFAULT_SOURCE_TEMPLATE = "LOGICAL.{name}"
DEFAULT_SCHEME_NAME = "metamesh_export"


def generate_osi_yaml(
    *,
    ontology_root: Path,
    naming: str = "dv_lower",
    source_template: str = DEFAULT_SOURCE_TEMPLATE,
    source_overrides: dict[str, str] | None = None,
    model_name_override: str | None = None,
) -> dict[str, Any]:
    """Build the OSI semantic-model dict for a given ontology root.

    Args:
        ontology_root: Directory containing ``concepts/`` and ``relationships/``.
        naming: Dataset naming strategy (same options as ``generate_dbt_yaml``).
        source_template: Format string used to generate ``Dataset.source``
            when no override is given. Available placeholder: ``{name}``.
        source_overrides: Optional mapping of dataset name → physical source
            string (例: ``{"hub_streamer": "PROD.ANALYTICS.HUB_STREAMER"}``)。
        model_name_override: Optional name for the top-level SemanticModel.
            Defaults to the ontology's ``skos:inScheme`` value if all bound
            concepts share one, otherwise ``metamesh_export``.

    Returns:
        OSI top-level dict suitable for ``yaml.safe_dump``.
    """
    validate_naming(naming)
    overrides = source_overrides or {}

    concepts = load_jsonld_dir(ontology_root / "concepts")
    relationships = load_jsonld_dir(ontology_root / "relationships")
    concept_index = {c["@id"]: c for c in concepts}

    datasets: list[dict[str, Any]] = []
    for c in concepts:
        ds = _concept_to_dataset(
            c,
            naming=naming,
            source_template=source_template,
            source_overrides=overrides,
        )
        if ds is not None:
            datasets.append(ds)

    osi_relationships: list[dict[str, Any]] = []
    for r in relationships:
        rel = _relationship_to_osi(
            r, naming=naming, concept_index=concept_index
        )
        if rel is not None:
            osi_relationships.append(rel)

    _detect_dataset_collisions(datasets)

    sm_name = model_name_override or _derive_semantic_model_name(concepts)
    sm: dict[str, Any] = {
        "name": sm_name,
        "datasets": datasets,
        "relationships": osi_relationships,
        "metrics": [],
    }

    return {
        "version": OSI_VERSION,
        "semantic_model": [sm],
    }


# ---------------------------------------------------------------------------
# Per-document transforms
# ---------------------------------------------------------------------------


def _concept_to_dataset(
    concept: dict[str, Any],
    *,
    naming: str,
    source_template: str,
    source_overrides: dict[str, str],
) -> dict[str, Any] | None:
    hub = concept.get("dv:hub")
    if not isinstance(hub, str) or not hub:
        # Concepts without a Hub don't bind to a physical table.
        return None

    cid = concept["@id"]
    name = model_name(concept, oid=cid, naming=naming)
    source = source_overrides.get(name) or source_template.format(name=name)

    ds: dict[str, Any] = {
        "name": name,
        "source": source,
    }

    business_key = concept.get("dv:business_key")
    if isinstance(business_key, str) and business_key:
        ds["primary_key"] = [business_key]

    description = _short_description(concept)
    if description:
        ds["description"] = description

    ai_context = _build_ai_context(concept)
    if ai_context:
        ds["ai_context"] = ai_context

    extensions = _build_common_extensions(concept, ontology_iri=cid)
    if extensions:
        ds["custom_extensions"] = extensions

    return ds


def _relationship_to_osi(
    rel: dict[str, Any],
    *,
    naming: str,
    concept_index: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    link = rel.get("dv:link")
    if not isinstance(link, str) or not link:
        return None

    rid = rel["@id"]
    domain_id = (rel.get("rdfs:domain") or {}).get("@id")
    range_id = (rel.get("rdfs:range") or {}).get("@id")
    if not domain_id or not range_id:
        logger.warning(
            "Skipping relationship %s: missing rdfs:domain or rdfs:range", rid
        )
        return None

    cardinality = rel.get("dv:cardinality") or ""
    domain_concept = concept_index.get(domain_id, {})
    range_concept = concept_index.get(range_id, {})

    # OSI: ``from`` is the many-side, ``to`` is the one-side。
    # ``1:N`` の場合は domain (1) → range (N) なので range が many-side。
    if cardinality == "1:N":
        from_concept_id, to_concept_id = range_id, domain_id
        from_concept, to_concept = range_concept, domain_concept
    elif cardinality == "N:M":
        # OSI に直接対応する概念がないので、junction dataset を別途切る必要がある。
        # 自動生成は危険なので skip + warn にとどめる。
        logger.warning(
            "Skipping relationship %s with cardinality N:M "
            "(OSI has no direct counterpart; would require a junction dataset)",
            rid,
        )
        return None
    else:
        # ``N:1``、``1:1``、未指定はそのまま (domain=many, range=one)。
        from_concept_id, to_concept_id = domain_id, range_id
        from_concept, to_concept = domain_concept, range_concept

    from_dataset = _dataset_name_for(from_concept, oid=from_concept_id, naming=naming)
    to_dataset = _dataset_name_for(to_concept, oid=to_concept_id, naming=naming)

    # OSI の relationship は from_columns / to_columns が必須かつ非空。
    # metamesh のオントロジーは FK 列名を持たないので、慣習として FK 列名は
    # 参照先 (to-side, one-side) の PK 列名と同じと仮定する。
    # 例: Channel.streamer_id (FK) → Streamer.streamer_id (PK) のケース。
    # 実環境で FK 列名が異なる場合は出力後に手動編集する想定。
    to_bk = to_concept.get("dv:business_key") or _fallback_key(to_concept_id)

    osi_rel: dict[str, Any] = {
        "name": model_name(rel, oid=rid, naming=naming),
        "from": from_dataset,
        "to": to_dataset,
        "from_columns": [to_bk],
        "to_columns": [to_bk],
    }

    extensions = _build_common_extensions(rel, ontology_iri=rid)
    if extensions:
        osi_rel["custom_extensions"] = extensions

    return osi_rel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dataset_name_for(
    concept: dict[str, Any], *, oid: str, naming: str
) -> str:
    """Resolve dataset name for a referenced concept (may be empty fallback)."""
    if concept:
        return model_name(concept, oid=oid, naming=naming)
    # Concept は ontology に存在しない / 参照だけある場合: snake fallback
    return snake(oid)


def _short_description(doc: dict[str, Any]) -> str:
    """One-line description = pref label (ja/en) + first sentence of definition."""
    pref_ja = label_for_lang(doc.get("skos:prefLabel"), "ja")
    pref_en = label_for_lang(doc.get("skos:prefLabel"), "en")
    def_ja = label_for_lang(doc.get("skos:definition"), "ja") or ""

    title = pref_ja or doc["@id"]
    if pref_en and pref_en != title:
        title = f"{title} ({pref_en})"

    short_def = def_ja.split("。")[0].strip()
    if short_def and not short_def.endswith("。"):
        short_def += "。"
    return f"{title}: {short_def}" if short_def else title


def _build_ai_context(doc: dict[str, Any]) -> dict[str, Any]:
    """Build OSI ``ai_context`` from skos definition / altLabel."""
    ctx: dict[str, Any] = {}

    def_ja = label_for_lang(doc.get("skos:definition"), "ja")
    def_en = label_for_lang(doc.get("skos:definition"), "en")
    instructions: list[str] = []
    if def_ja:
        instructions.append(def_ja)
    if def_en and def_en != def_ja:
        instructions.append(def_en)
    if instructions:
        ctx["instructions"] = "\n\n".join(instructions)

    synonyms = _flatten_alt_labels(doc.get("skos:altLabel"))
    if synonyms:
        ctx["synonyms"] = synonyms

    return ctx


def _flatten_alt_labels(values: Any) -> list[str]:
    """``skos:altLabel`` の dict|list を ja/en 区別なく flat な list に。"""
    if not values:
        return []
    if isinstance(values, dict):
        values = [values]
    out: list[str] = []
    seen: set[str] = set()
    for v in values:
        if isinstance(v, dict):
            val = v.get("@value")
            if isinstance(val, str) and val and val not in seen:
                out.append(val)
                seen.add(val)
    return out


def _build_common_extensions(
    doc: dict[str, Any], *, ontology_iri: str
) -> list[dict[str, Any]]:
    """OSI ``custom_extensions`` (vendor_name: COMMON) に metamesh 拡張を埋める。

    OSI の vendor enum は固定なので独自 vendor 名は使えない。COMMON 配下の
    JSON 文字列に ``metamesh_iri`` と ``dv``/``kimball`` 拡張を保持する。
    OSI 受け取り側からは opaque だが、metamesh 側では完全復元できる。
    """
    extension_payload: dict[str, Any] = {"metamesh_iri": ontology_iri}
    for ns in EXT_NAMESPACES:
        prefix = ns + ":"
        ns_payload = {
            k[len(prefix):]: v for k, v in doc.items() if k.startswith(prefix)
        }
        if ns_payload:
            extension_payload[ns] = ns_payload

    return [
        {
            "vendor_name": "COMMON",
            "data": json.dumps(extension_payload, ensure_ascii=False, sort_keys=True),
        }
    ]


def _detect_dataset_collisions(datasets: list[dict[str, Any]]) -> None:
    """Two datasets with the same name break OSI uniqueness."""
    seen: dict[str, int] = {}
    for ds in datasets:
        seen[ds["name"]] = seen.get(ds["name"], 0) + 1
    dupes = sorted(name for name, n in seen.items() if n > 1)
    if dupes:
        raise ValueError(
            "duplicate OSI dataset name(s) generated from ontology: "
            f"{dupes}. Resolve at the ontology level (typically: keep DV "
            "extension metadata on exactly one of Concept vs Relationship)."
        )


def _derive_semantic_model_name(concepts: list[dict[str, Any]]) -> str:
    """Single ``skos:inScheme`` を持っていればそれを model 名に流用。"""
    schemes: set[str] = set()
    for c in concepts:
        scheme = (c.get("skos:inScheme") or {}).get("@id")
        if scheme:
            schemes.add(scheme)
    if len(schemes) == 1:
        return next(iter(schemes))
    return DEFAULT_SCHEME_NAME


def _fallback_key(concept_id: str) -> str:
    """Best-effort guess when a related concept lacks ``dv:business_key``."""
    return f"{snake(concept_id)}_id"
