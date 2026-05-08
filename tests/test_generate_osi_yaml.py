"""generate_osi_yaml の動作検証。

vtuber-analytics ライクな構成 (Streamer / Channel / owns_channel) を
fixture で組み立てて、OSI v0.1.1 dict が期待形になることを確認する。
フォーマット (YAML 文字列) ではなく dict 構造で assert することで、
改行や順序の差異に脆くしない。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from metamesh.generators.osi import (
    OSI_VERSION,
    generate_osi_yaml,
)
from metamesh.ontology.store import ConceptStore


@pytest.fixture
def populated_root(tmp_path: Path) -> Path:
    """Streamer (1) → Channel (N) と Streamer-Streamer の N:M Collaboration の最小オントロジー。"""
    store = ConceptStore(tmp_path)
    store.save_concept(
        concept_id="Streamer",
        pref_label_ja="配信者",
        definition_ja="VTuber 個人。",
        pref_label_en="Streamer",
        definition_en="A VTuber individual.",
        alt_labels_ja=["VTuber", "ライバー"],
        alt_labels_en=["VTuber", "Talent"],
        broader=None,
        narrower=[],
        related=["Channel"],
        scheme="VTuberDomain",
        extension={
            "namespace": "dv",
            "data": {"hub": "HUB_STREAMER", "business_key": "streamer_id"},
        },
    )
    store.save_concept(
        concept_id="Channel",
        pref_label_ja="チャンネル",
        definition_ja="配信枠。",
        pref_label_en=None,
        definition_en=None,
        alt_labels_ja=[],
        alt_labels_en=[],
        broader=None,
        narrower=[],
        related=[],
        scheme="VTuberDomain",
        extension={
            "namespace": "dv",
            "data": {"hub": "HUB_CHANNEL", "business_key": "channel_id"},
        },
    )
    # Hub を持たない pure-SKOS concept (skip 対象)
    store.save_concept(
        concept_id="Topic",
        pref_label_ja="トピック",
        definition_ja="配信のテーマ分類。",
        pref_label_en=None,
        definition_en=None,
        alt_labels_ja=[],
        alt_labels_en=[],
        broader=None,
        narrower=[],
        related=[],
        scheme="VTuberDomain",
        extension=None,
    )
    store.save_relationship(
        relationship_id="owns_channel",
        pref_label_ja="チャンネルを所有する",
        definition_ja="配信者がチャンネルを所有する関係。",
        domain="Streamer",
        range_="Channel",
        pref_label_en="owns channel",
        definition_en=None,
        inverse_of=None,
        scheme="VTuberDomain",
        extension={
            "namespace": "dv",
            "data": {"link": "LNK_STREAMER_CHANNEL", "cardinality": "1:N"},
        },
    )
    # link を持たない relationship (skip 対象)
    store.save_relationship(
        relationship_id="categorized_as",
        pref_label_ja="〜にカテゴリされる",
        definition_ja="配信が Topic にカテゴライズされる。",
        domain="Streamer",
        range_="Topic",
        pref_label_en=None,
        definition_en=None,
        inverse_of=None,
        scheme="VTuberDomain",
        extension=None,
    )
    return tmp_path


def test_top_level_shape(populated_root: Path) -> None:
    out = generate_osi_yaml(ontology_root=populated_root)
    assert out["version"] == OSI_VERSION
    assert isinstance(out["semantic_model"], list)
    assert len(out["semantic_model"]) == 1
    sm = out["semantic_model"][0]
    assert sm["name"] == "VTuberDomain"  # 単一 skos:inScheme から派生
    assert "datasets" in sm
    assert "relationships" in sm
    assert sm["metrics"] == []


def test_dataset_emission_skips_non_hub_concepts(populated_root: Path) -> None:
    out = generate_osi_yaml(ontology_root=populated_root)
    datasets = out["semantic_model"][0]["datasets"]
    names = {ds["name"] for ds in datasets}
    # Streamer / Channel は dv:hub あるので emit、Topic は skip
    assert names == {"hub_streamer", "hub_channel"}


def test_relationship_emission_skips_non_link(populated_root: Path) -> None:
    out = generate_osi_yaml(ontology_root=populated_root)
    rels = out["semantic_model"][0]["relationships"]
    names = {r["name"] for r in rels}
    # owns_channel は dv:link あるので emit、categorized_as は skip
    assert names == {"lnk_streamer_channel"}


def test_dataset_source_default_template(populated_root: Path) -> None:
    out = generate_osi_yaml(ontology_root=populated_root)
    datasets = {ds["name"]: ds for ds in out["semantic_model"][0]["datasets"]}
    assert datasets["hub_streamer"]["source"] == "LOGICAL.hub_streamer"
    assert datasets["hub_channel"]["source"] == "LOGICAL.hub_channel"


def test_dataset_source_overrides(populated_root: Path) -> None:
    out = generate_osi_yaml(
        ontology_root=populated_root,
        source_overrides={"hub_streamer": "PROD.ANALYTICS.HUB_STREAMER"},
    )
    datasets = {ds["name"]: ds for ds in out["semantic_model"][0]["datasets"]}
    assert datasets["hub_streamer"]["source"] == "PROD.ANALYTICS.HUB_STREAMER"
    # override 指定がない方は default template
    assert datasets["hub_channel"]["source"] == "LOGICAL.hub_channel"


def test_dataset_primary_key(populated_root: Path) -> None:
    out = generate_osi_yaml(ontology_root=populated_root)
    datasets = {ds["name"]: ds for ds in out["semantic_model"][0]["datasets"]}
    assert datasets["hub_streamer"]["primary_key"] == ["streamer_id"]
    assert datasets["hub_channel"]["primary_key"] == ["channel_id"]


def test_dataset_ai_context(populated_root: Path) -> None:
    out = generate_osi_yaml(ontology_root=populated_root)
    datasets = {ds["name"]: ds for ds in out["semantic_model"][0]["datasets"]}
    streamer_ctx = datasets["hub_streamer"]["ai_context"]
    # 多言語 altLabel が ja/en 区別なく flat な list で synonyms に入る
    assert "VTuber" in streamer_ctx["synonyms"]
    assert "ライバー" in streamer_ctx["synonyms"]
    assert "Talent" in streamer_ctx["synonyms"]
    # ja + en の definition が結合されて instructions に
    assert "VTuber 個人。" in streamer_ctx["instructions"]
    assert "A VTuber individual." in streamer_ctx["instructions"]


def test_dataset_custom_extension_carries_dv(populated_root: Path) -> None:
    out = generate_osi_yaml(ontology_root=populated_root)
    datasets = {ds["name"]: ds for ds in out["semantic_model"][0]["datasets"]}
    ext = datasets["hub_streamer"]["custom_extensions"]
    assert len(ext) == 1
    assert ext[0]["vendor_name"] == "COMMON"
    payload = json.loads(ext[0]["data"])
    assert payload["metamesh_iri"] == "Streamer"
    assert payload["dv"]["hub"] == "HUB_STREAMER"
    assert payload["dv"]["business_key"] == "streamer_id"


def test_relationship_swaps_for_one_to_many(populated_root: Path) -> None:
    """1:N の場合は OSI 慣習で from=many-side (range), to=one-side (domain)。"""
    out = generate_osi_yaml(ontology_root=populated_root)
    rel = out["semantic_model"][0]["relationships"][0]
    # owns_channel: Streamer (1) → Channel (N), cardinality 1:N
    # OSI: from=Channel (many), to=Streamer (one)
    assert rel["from"] == "hub_channel"
    assert rel["to"] == "hub_streamer"
    # FK 列名は to-side の business_key と同じと仮定 (慣習)
    assert rel["from_columns"] == ["streamer_id"]
    assert rel["to_columns"] == ["streamer_id"]


def test_relationship_no_swap_for_many_to_one(tmp_path: Path) -> None:
    """N:1 の場合は from=domain (many), to=range (one) でそのまま。"""
    store = ConceptStore(tmp_path)
    store.save_concept(
        concept_id="Channel",
        pref_label_ja="チャンネル",
        definition_ja=None,
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
            "data": {"hub": "HUB_CHANNEL", "business_key": "channel_id"},
        },
    )
    store.save_concept(
        concept_id="Streamer",
        pref_label_ja="配信者",
        definition_ja=None,
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
            "data": {"hub": "HUB_STREAMER", "business_key": "streamer_id"},
        },
    )
    store.save_relationship(
        relationship_id="belongs_to_streamer",
        pref_label_ja="配信者に属する",
        definition_ja=None,
        domain="Channel",
        range_="Streamer",
        pref_label_en=None,
        definition_en=None,
        inverse_of=None,
        scheme=None,
        extension={
            "namespace": "dv",
            "data": {"link": "LNK_CHANNEL_STREAMER", "cardinality": "N:1"},
        },
    )
    out = generate_osi_yaml(ontology_root=tmp_path)
    rel = out["semantic_model"][0]["relationships"][0]
    # N:1: domain=Channel (many), range=Streamer (one)
    assert rel["from"] == "hub_channel"
    assert rel["to"] == "hub_streamer"
    assert rel["to_columns"] == ["streamer_id"]


def test_relationship_skips_n_to_m(tmp_path: Path) -> None:
    """N:M は OSI 直接対応がないので skip される。"""
    store = ConceptStore(tmp_path)
    store.save_concept(
        concept_id="Streamer",
        pref_label_ja=None,
        definition_ja=None,
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
            "data": {"hub": "HUB_STREAMER", "business_key": "streamer_id"},
        },
    )
    store.save_relationship(
        relationship_id="collaborates_with",
        pref_label_ja=None,
        definition_ja=None,
        domain="Streamer",
        range_="Streamer",
        pref_label_en=None,
        definition_en=None,
        inverse_of=None,
        scheme=None,
        extension={
            "namespace": "dv",
            "data": {"link": "LNK_COLLAB", "cardinality": "N:M"},
        },
    )
    out = generate_osi_yaml(ontology_root=tmp_path)
    assert out["semantic_model"][0]["relationships"] == []


def test_model_name_override(populated_root: Path) -> None:
    out = generate_osi_yaml(
        ontology_root=populated_root, model_name_override="VTuber"
    )
    assert out["semantic_model"][0]["name"] == "VTuber"


def test_default_model_name_when_no_scheme(tmp_path: Path) -> None:
    store = ConceptStore(tmp_path)
    store.save_concept(
        concept_id="Foo",
        pref_label_ja=None,
        definition_ja=None,
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
            "data": {"hub": "HUB_FOO", "business_key": "foo_id"},
        },
    )
    out = generate_osi_yaml(ontology_root=tmp_path)
    assert out["semantic_model"][0]["name"] == "metamesh_export"


def test_naming_strategies(populated_root: Path) -> None:
    out_as_is = generate_osi_yaml(ontology_root=populated_root, naming="as_is")
    names_as_is = {ds["name"] for ds in out_as_is["semantic_model"][0]["datasets"]}
    assert names_as_is == {"Streamer", "Channel"}

    out_snake = generate_osi_yaml(ontology_root=populated_root, naming="snake")
    names_snake = {ds["name"] for ds in out_snake["semantic_model"][0]["datasets"]}
    assert names_snake == {"streamer", "channel"}


def test_empty_ontology(tmp_path: Path) -> None:
    """concepts/ も relationships/ も空のオントロジーで死なない。"""
    out = generate_osi_yaml(ontology_root=tmp_path)
    assert out["version"] == OSI_VERSION
    sm = out["semantic_model"][0]
    assert sm["datasets"] == []
    assert sm["relationships"] == []
    assert sm["metrics"] == []


def test_output_matches_osi_v011_jsonschema(populated_root: Path) -> None:
    """vendor された OSI v0.1.1 公式 JSON Schema で生成 dict を検証する。

    OSI 仕様 (https://github.com/open-semantic-interchange/OSI/blob/main/core-spec/osi-schema.json)
    の SemanticModel を minItems: 1 で強制するため、空オントロジーは
    通らない。populated_root を使う。
    """
    jsonschema = pytest.importorskip("jsonschema")
    schema_path = Path(__file__).parent / "data" / "osi-schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    out = generate_osi_yaml(ontology_root=populated_root)
    # raises on failure
    jsonschema.validate(instance=out, schema=schema)
