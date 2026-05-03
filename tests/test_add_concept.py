"""ConceptStore のラウンドトリップ検証。

JSON-LD の構造を直接 assert すると壊れやすいので、rdflib でグラフ化してトリプル単位で検証する。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import SKOS

from metamesh.ontology.store import BASE_NS, ConceptStore


@pytest.fixture
def store(tmp_path: Path) -> ConceptStore:
    return ConceptStore(tmp_path)


def _load(path: Path) -> Graph:
    g = Graph()
    g.parse(data=path.read_text(encoding="utf-8"), format="json-ld")
    return g


def test_minimal_concept_round_trips(store: ConceptStore) -> None:
    path = store.save_concept(
        concept_id="Streamer",
        pref_label_ja="配信者",
        definition_ja="VTuber 個人を表す概念",
        pref_label_en=None,
        definition_en=None,
        alt_labels_ja=[],
        alt_labels_en=[],
        broader=None,
        narrower=[],
        related=[],
        scheme=None,
        extension=None,
    )

    g = _load(path)
    subj = URIRef(BASE_NS + "Streamer")

    assert (subj, SKOS.prefLabel, Literal("配信者", lang="ja")) in g
    assert (subj, SKOS.definition, Literal("VTuber 個人を表す概念", lang="ja")) in g


def test_multilingual_with_synonyms(store: ConceptStore) -> None:
    path = store.save_concept(
        concept_id="Customer",
        pref_label_ja="顧客",
        definition_ja="商品を購入する主体",
        pref_label_en="Customer",
        definition_en="An entity that purchases goods",
        alt_labels_ja=["得意先", "お客様"],
        alt_labels_en=["Account"],
        broader=None,
        narrower=[],
        related=[],
        scheme=None,
        extension=None,
    )

    g = _load(path)
    subj = URIRef(BASE_NS + "Customer")

    alt_labels = set(g.objects(subj, SKOS.altLabel))
    assert Literal("得意先", lang="ja") in alt_labels
    assert Literal("お客様", lang="ja") in alt_labels
    assert Literal("Account", lang="en") in alt_labels


def test_hierarchy_links(store: ConceptStore) -> None:
    path = store.save_concept(
        concept_id="HololiveStreamer",
        pref_label_ja="ホロライブ所属配信者",
        definition_ja="ホロライブプロダクションに所属する VTuber",
        pref_label_en=None,
        definition_en=None,
        alt_labels_ja=[],
        alt_labels_en=[],
        broader="Streamer",
        narrower=["Gen0Streamer", "Gen1Streamer"],
        related=[],
        scheme="VTuberDomain",
        extension=None,
    )

    g = _load(path)
    subj = URIRef(BASE_NS + "HololiveStreamer")

    assert (subj, SKOS.broader, URIRef(BASE_NS + "Streamer")) in g
    narrower = set(g.objects(subj, SKOS.narrower))
    assert URIRef(BASE_NS + "Gen0Streamer") in narrower
    assert URIRef(BASE_NS + "Gen1Streamer") in narrower
    assert (subj, SKOS.inScheme, URIRef(BASE_NS + "VTuberDomain")) in g


def test_dv_extension_namespace(store: ConceptStore) -> None:
    path = store.save_concept(
        concept_id="Stream",
        pref_label_ja="配信",
        definition_ja="1 回の配信イベント",
        pref_label_en=None,
        definition_en=None,
        alt_labels_ja=[],
        alt_labels_en=[],
        broader=None,
        narrower=[],
        related=[],
        scheme=None,
        extension={
            "namespace": "dv",
            "data": {"hub": "HUB_STREAM", "businessKey": "video_id"},
        },
    )

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["@context"]["dv"] == "https://metamesh.dev/ext/dv/"
    assert raw["dv:hub"] == "HUB_STREAM"
    assert raw["dv:businessKey"] == "video_id"


def test_unknown_extension_namespace_rejected(store: ConceptStore) -> None:
    with pytest.raises(ValueError, match="unknown extension namespace"):
        store.save_concept(
            concept_id="Bogus",
            pref_label_ja="ダミー",
            definition_ja="テスト用",
            pref_label_en=None,
            definition_en=None,
            alt_labels_ja=[],
            alt_labels_en=[],
            broader=None,
            narrower=[],
            related=[],
            scheme=None,
            extension={"namespace": "unknown", "data": {"x": 1}},
        )


def test_invalid_concept_id_rejected(store: ConceptStore) -> None:
    with pytest.raises(ValueError, match="invalid concept_id"):
        store.save_concept(
            concept_id="../escape",
            pref_label_ja="x",
            definition_ja="x",
            pref_label_en=None,
            definition_en=None,
            alt_labels_ja=[],
            alt_labels_en=[],
            broader=None,
            narrower=[],
            related=[],
            scheme=None,
            extension=None,
        )


def test_multiple_extensions_coexist(store: ConceptStore) -> None:
    """DV と Kimball 拡張を同じ Concept に共存させる (Issue #21)。"""
    path = store.save_concept(
        concept_id="Streamer",
        pref_label_ja="配信者",
        definition_ja="VTuber 個人を表す概念",
        pref_label_en=None,
        definition_en=None,
        alt_labels_ja=[],
        alt_labels_en=[],
        broader=None,
        narrower=[],
        related=[],
        scheme=None,
        extension=[
            {"namespace": "dv", "data": {"hub": "HUB_STREAMER", "business_key": "channel_id"}},
            {"namespace": "kimball", "data": {"dimension": "dim_streamer", "scd_type": 2}},
        ],
    )

    raw = json.loads(path.read_text(encoding="utf-8"))
    # Both namespaces present in @context
    assert raw["@context"]["dv"] == "https://metamesh.dev/ext/dv/"
    assert raw["@context"]["kimball"] == "https://metamesh.dev/ext/kimball/"
    # Both extensions' data merged into the document
    assert raw["dv:hub"] == "HUB_STREAMER"
    assert raw["dv:business_key"] == "channel_id"
    assert raw["kimball:dimension"] == "dim_streamer"
    assert raw["kimball:scd_type"] == 2


def test_multiple_extensions_same_namespace_last_wins(store: ConceptStore) -> None:
    """同 namespace を二重に渡した場合は last-wins (incremental overlay 用途)。"""
    path = store.save_concept(
        concept_id="Streamer",
        pref_label_ja="配信者",
        definition_ja="x",
        pref_label_en=None,
        definition_en=None,
        alt_labels_ja=[],
        alt_labels_en=[],
        broader=None,
        narrower=[],
        related=[],
        scheme=None,
        extension=[
            {"namespace": "dv", "data": {"hub": "HUB_OLD"}},
            {"namespace": "dv", "data": {"hub": "HUB_NEW", "business_key": "id"}},
        ],
    )

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["dv:hub"] == "HUB_NEW"  # later overrides earlier
    assert raw["dv:business_key"] == "id"  # later-only key still present


def test_single_extension_dict_still_works(store: ConceptStore) -> None:
    """Backward compat: pre-#21 callers passing a single dict keep working."""
    path = store.save_concept(
        concept_id="Channel",
        pref_label_ja="チャンネル",
        definition_ja="x",
        pref_label_en=None,
        definition_en=None,
        alt_labels_ja=[],
        alt_labels_en=[],
        broader=None,
        narrower=[],
        related=[],
        scheme=None,
        extension={"namespace": "dv", "data": {"hub": "HUB_CHANNEL"}},
    )
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["dv:hub"] == "HUB_CHANNEL"
    assert "kimball:dimension" not in raw


def test_invalid_extension_type_rejected(store: ConceptStore) -> None:
    with pytest.raises(TypeError, match="extension must be"):
        store.save_concept(
            concept_id="Bad",
            pref_label_ja="x",
            definition_ja="x",
            pref_label_en=None,
            definition_en=None,
            alt_labels_ja=[],
            alt_labels_en=[],
            broader=None,
            narrower=[],
            related=[],
            scheme=None,
            extension="not a dict or list",  # type: ignore[arg-type]
        )


def test_unknown_namespace_in_list_still_rejected(store: ConceptStore) -> None:
    """混在 list の中に unknown namespace があれば全体が落ちる (atomicity)。"""
    with pytest.raises(ValueError, match="unknown extension namespace"):
        store.save_concept(
            concept_id="Mixed",
            pref_label_ja="x",
            definition_ja="x",
            pref_label_en=None,
            definition_en=None,
            alt_labels_ja=[],
            alt_labels_en=[],
            broader=None,
            narrower=[],
            related=[],
            scheme=None,
            extension=[
                {"namespace": "dv", "data": {"hub": "HUB_X"}},
                {"namespace": "bogus", "data": {"x": 1}},
            ],
        )
