"""generate_semantic_layer の動作検証。"""
from __future__ import annotations

from pathlib import Path

import pytest

from metamesh.generators.semantic_layer import generate_semantic_layer
from metamesh.ontology.store import ConceptStore


@pytest.fixture
def populated_root(tmp_path: Path) -> Path:
    store = ConceptStore(tmp_path)
    # Hub concept with business_key
    store.save_concept(
        concept_id="Streamer",
        pref_label_ja="配信者",
        definition_ja="VTuber 個人。配信を行う主体。",
        pref_label_en="Streamer",
        definition_en=None,
        alt_labels_ja=[],
        alt_labels_en=[],
        broader=None,
        narrower=[],
        related=[],
        scheme=None,
        extension={"namespace": "dv", "data": {"hub": "HUB_STREAMER", "business_key": "streamer_id"}},
    )
    store.save_concept(
        concept_id="Channel",
        pref_label_ja="チャンネル",
        definition_ja="配信枠",
        pref_label_en=None,
        definition_en=None,
        alt_labels_ja=[],
        alt_labels_en=[],
        broader=None,
        narrower=[],
        related=[],
        scheme=None,
        extension={"namespace": "dv", "data": {"hub": "HUB_CHANNEL", "business_key": "channel_id"}},
    )
    # Pure SKOS concept (no DV) — should be skipped
    store.save_concept(
        concept_id="Collaboration",
        pref_label_ja="コラボ",
        definition_ja="複数人配信",
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
    # Link relationship
    store.save_relationship(
        relationship_id="owns_channel",
        pref_label_ja="チャンネルを所有する",
        definition_ja="配信者がチャンネルを所有する関係。",
        domain="Streamer",
        range_="Channel",
        pref_label_en=None,
        definition_en=None,
        inverse_of=None,
        scheme=None,
        extension={"namespace": "dv", "data": {"link": "LNK_STREAMER_CHANNEL", "cardinality": "1:N"}},
    )
    # Pure relationship without DV link — should be skipped
    store.save_relationship(
        relationship_id="bare_rel",
        pref_label_ja="裸の関係",
        definition_ja="DV 拡張なし",
        domain="Streamer",
        range_="Channel",
        pref_label_en=None,
        definition_en=None,
        inverse_of=None,
        scheme=None,
        extension=None,
    )
    return tmp_path


def test_top_level_shape(populated_root: Path) -> None:
    out = generate_semantic_layer(ontology_root=populated_root)
    assert "semantic_models" in out
    assert "metrics" in out
    assert out["metrics"] == []


def test_only_dv_bound_elements_emitted(populated_root: Path) -> None:
    """Concepts/relationships without DV hub/link must be skipped."""
    out = generate_semantic_layer(ontology_root=populated_root)
    names = [sm["name"] for sm in out["semantic_models"]]
    # 2 hubs + 1 link = 3 (Collaboration and bare_rel skipped)
    assert len(names) == 3
    assert "hub_streamer" in names
    assert "hub_channel" in names
    assert "lnk_streamer_channel" in names


def test_hub_concept_has_primary_entity_with_business_key(populated_root: Path) -> None:
    out = generate_semantic_layer(ontology_root=populated_root)
    hub = next(sm for sm in out["semantic_models"] if sm["name"] == "hub_streamer")
    assert hub["model"] == "ref('hub_streamer')"
    assert len(hub["entities"]) == 1
    ent = hub["entities"][0]
    assert ent == {"name": "streamer", "type": "primary", "expr": "streamer_id"}


def test_link_relationship_has_two_foreign_entities_with_fk_lookup(populated_root: Path) -> None:
    out = generate_semantic_layer(ontology_root=populated_root)
    lnk = next(sm for sm in out["semantic_models"] if sm["name"] == "lnk_streamer_channel")
    assert lnk["model"] == "ref('lnk_streamer_channel')"
    assert len(lnk["entities"]) == 2
    by_name = {e["name"]: e for e in lnk["entities"]}
    assert by_name["streamer"] == {"name": "streamer", "type": "foreign", "expr": "streamer_id"}
    assert by_name["channel"] == {"name": "channel", "type": "foreign", "expr": "channel_id"}


def test_self_link_disambiguates_entity_names(tmp_path: Path) -> None:
    """When domain == range, the second foreign entity gets a suffix to stay unique."""
    store = ConceptStore(tmp_path)
    store.save_concept(
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
        extension={"namespace": "dv", "data": {"hub": "HUB_STREAMER", "business_key": "streamer_id"}},
    )
    store.save_relationship(
        relationship_id="follows",
        pref_label_ja="フォローする",
        definition_ja="配信者間の関係",
        domain="Streamer",
        range_="Streamer",
        pref_label_en=None,
        definition_en=None,
        inverse_of=None,
        scheme=None,
        extension={"namespace": "dv", "data": {"link": "LNK_FOLLOW"}},
    )
    out = generate_semantic_layer(ontology_root=tmp_path)
    lnk = next(sm for sm in out["semantic_models"] if sm["name"] == "lnk_follow")
    names = [e["name"] for e in lnk["entities"]]
    assert names == ["streamer", "streamer_other"]


def test_fallback_business_key_when_concept_unknown(tmp_path: Path) -> None:
    """If the relationship references a concept with no DV bk, fall back to <snake>_id."""
    store = ConceptStore(tmp_path)
    # Note: Source concept has no business_key
    store.save_concept(
        concept_id="MysteryConcept",
        pref_label_ja="謎",
        definition_ja="x",
        pref_label_en=None,
        definition_en=None,
        alt_labels_ja=[],
        alt_labels_en=[],
        broader=None,
        narrower=[],
        related=[],
        scheme=None,
        extension={"namespace": "dv", "data": {"hub": "HUB_MYSTERY"}},  # no business_key
    )
    store.save_concept(
        concept_id="OtherConcept",
        pref_label_ja="他",
        definition_ja="x",
        pref_label_en=None,
        definition_en=None,
        alt_labels_ja=[],
        alt_labels_en=[],
        broader=None,
        narrower=[],
        related=[],
        scheme=None,
        extension={"namespace": "dv", "data": {"hub": "HUB_OTHER"}},
    )
    store.save_relationship(
        relationship_id="rel_x",
        pref_label_ja="x",
        definition_ja="x",
        domain="MysteryConcept",
        range_="OtherConcept",
        pref_label_en=None,
        definition_en=None,
        inverse_of=None,
        scheme=None,
        extension={"namespace": "dv", "data": {"link": "LNK_X"}},
    )
    out = generate_semantic_layer(ontology_root=tmp_path)
    # primary entity on hub_mystery falls back to mystery_concept_id
    hub = next(sm for sm in out["semantic_models"] if sm["name"] == "hub_mystery")
    assert hub["entities"][0]["expr"] == "mystery_concept_id"
    # foreign entity in lnk_x also falls back
    lnk = next(sm for sm in out["semantic_models"] if sm["name"] == "lnk_x")
    by_name = {e["name"]: e for e in lnk["entities"]}
    assert by_name["mystery_concept"]["expr"] == "mystery_concept_id"


def test_unknown_naming_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown naming strategy"):
        generate_semantic_layer(ontology_root=tmp_path, naming="bogus")


def test_empty_ontology_returns_empty(tmp_path: Path) -> None:
    (tmp_path / "concepts").mkdir()
    (tmp_path / "relationships").mkdir()
    out = generate_semantic_layer(ontology_root=tmp_path)
    assert out == {"semantic_models": [], "metrics": []}


def test_collision_between_concept_and_relationship_raises(tmp_path: Path) -> None:
    store = ConceptStore(tmp_path)
    store.save_concept(
        concept_id="Collaboration",
        pref_label_ja="コラボ",
        definition_ja="x",
        pref_label_en=None,
        definition_en=None,
        alt_labels_ja=[],
        alt_labels_en=[],
        broader=None,
        narrower=[],
        related=[],
        scheme=None,
        extension={"namespace": "dv", "data": {"hub": "LNK_COLLAB"}},  # mistakenly tagged as hub
    )
    store.save_relationship(
        relationship_id="participates_in",
        pref_label_ja="出演",
        definition_ja="x",
        domain="Collaboration",
        range_="Collaboration",
        pref_label_en=None,
        definition_en=None,
        inverse_of=None,
        scheme=None,
        extension={"namespace": "dv", "data": {"link": "LNK_COLLAB"}},
    )
    with pytest.raises(ValueError, match="duplicate semantic_model"):
        generate_semantic_layer(ontology_root=tmp_path)
