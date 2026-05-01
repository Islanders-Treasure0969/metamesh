"""generate_dbt_yaml の動作検証。

ontology ディレクトリを fixture で組み立てて、dbt schema.yml dict が
期待形になることを確認する。フォーマット (YAML 文字列) ではなく
dict 構造で assert することで、改行や順序の差異に脆くしない。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from metamesh.generators.dbt_yaml import generate_dbt_yaml
from metamesh.ontology.store import ConceptStore


@pytest.fixture
def populated_root(tmp_path: Path) -> Path:
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
        related=["Channel", "Stream"],
        scheme="VTuberDomain",
        extension={"namespace": "dv", "data": {"hub": "HUB_STREAMER", "business_key": "channel_id"}},
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
        scheme=None,
        extension={"namespace": "dv", "data": {"hub": "HUB_CHANNEL"}},
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
        extension={"namespace": "dv", "data": {"link": "LNK_STREAMER_CHANNEL", "cardinality": "1:N"}},
    )
    return tmp_path


def test_top_level_shape(populated_root: Path) -> None:
    out = generate_dbt_yaml(ontology_root=populated_root)
    assert out["version"] == 2
    assert isinstance(out["models"], list)
    # 2 concepts + 1 relationship
    assert len(out["models"]) == 3
    assert {m["name"] for m in out["models"]} == {
        "hub_streamer",
        "hub_channel",
        "lnk_streamer_channel",
    }


def test_naming_as_is(populated_root: Path) -> None:
    out = generate_dbt_yaml(ontology_root=populated_root, naming="as_is")
    names = {m["name"] for m in out["models"]}
    assert names == {"Streamer", "Channel", "owns_channel"}


def test_naming_snake(populated_root: Path) -> None:
    out = generate_dbt_yaml(ontology_root=populated_root, naming="snake")
    names = {m["name"] for m in out["models"]}
    assert names == {"streamer", "channel", "owns_channel"}


def test_unknown_naming_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown naming strategy"):
        generate_dbt_yaml(ontology_root=tmp_path, naming="bogus")


def test_concept_description_includes_labels_and_synonyms(populated_root: Path) -> None:
    out = generate_dbt_yaml(ontology_root=populated_root)
    streamer = next(m for m in out["models"] if m["meta"]["ontology_id"] == "Streamer")
    desc = streamer["description"]
    assert "配信者" in desc
    assert "Streamer" in desc
    assert "VTuber 個人" in desc
    assert "A VTuber individual" in desc
    assert "ライバー" in desc
    assert "Talent" in desc


def test_concept_meta_includes_ontology_links_and_dv_extension(populated_root: Path) -> None:
    out = generate_dbt_yaml(ontology_root=populated_root)
    streamer = next(m for m in out["models"] if m["meta"]["ontology_id"] == "Streamer")
    meta = streamer["meta"]
    assert meta["ontology_type"] == "concept"
    assert meta["ontology_scheme"] == "VTuberDomain"
    assert set(meta["ontology_related"]) == {"Channel", "Stream"}
    assert meta["dv"] == {"hub": "HUB_STREAMER", "business_key": "channel_id"}


def test_relationship_meta_carries_domain_range_and_link(populated_root: Path) -> None:
    out = generate_dbt_yaml(ontology_root=populated_root)
    rel = next(m for m in out["models"] if m["meta"]["ontology_id"] == "owns_channel")
    meta = rel["meta"]
    assert meta["ontology_type"] == "relationship"
    assert meta["ontology_domain"] == "Streamer"
    assert meta["ontology_range"] == "Channel"
    assert meta["ontology_scheme"] == "VTuberDomain"
    assert meta["dv"]["link"] == "LNK_STREAMER_CHANNEL"
    assert meta["dv"]["cardinality"] == "1:N"


def test_relationship_description_shows_domain_arrow_range(populated_root: Path) -> None:
    out = generate_dbt_yaml(ontology_root=populated_root)
    rel = next(m for m in out["models"] if m["meta"]["ontology_id"] == "owns_channel")
    desc = rel["description"]
    assert "Streamer" in desc and "Channel" in desc
    assert "→" in desc
    assert "1:N" in desc


def test_empty_ontology_returns_empty_models(tmp_path: Path) -> None:
    # Create empty concepts/ and relationships/ dirs
    (tmp_path / "concepts").mkdir()
    (tmp_path / "relationships").mkdir()
    out = generate_dbt_yaml(ontology_root=tmp_path)
    assert out == {"version": 2, "models": []}


def test_collision_between_concept_and_relationship_raises(tmp_path: Path) -> None:
    """Concept and Relationship that share a DV link must not collapse to the same model."""
    store = ConceptStore(tmp_path)
    store.save_concept(
        concept_id="Collaboration",
        pref_label_ja="コラボ",
        definition_ja="複数配信者の同時出演",
        pref_label_en=None,
        definition_en=None,
        alt_labels_ja=[],
        alt_labels_en=[],
        broader=None,
        narrower=[],
        related=[],
        scheme=None,
        extension={"namespace": "dv", "data": {"link": "LNK_COLLAB"}},
    )
    store.save_relationship(
        relationship_id="participates_in",
        pref_label_ja="出演する",
        definition_ja="配信者が配信に出演",
        domain="Streamer",
        range_="Stream",
        pref_label_en=None,
        definition_en=None,
        inverse_of=None,
        scheme=None,
        extension={"namespace": "dv", "data": {"link": "LNK_COLLAB"}},
    )
    with pytest.raises(ValueError, match="duplicate dbt model name"):
        generate_dbt_yaml(ontology_root=tmp_path)


def test_concept_with_no_dv_falls_back_to_snake(tmp_path: Path) -> None:
    store = ConceptStore(tmp_path)
    store.save_concept(
        concept_id="MyOddConcept",
        pref_label_ja="奇妙な概念",
        definition_ja="拡張無し",
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
    out = generate_dbt_yaml(ontology_root=tmp_path, naming="dv_lower")
    assert out["models"][0]["name"] == "my_odd_concept"
