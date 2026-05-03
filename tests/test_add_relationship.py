"""ConceptStore.save_relationship のラウンドトリップ検証。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from metamesh.ontology.store import BASE_NS, ConceptStore


@pytest.fixture
def store(tmp_path: Path) -> ConceptStore:
    return ConceptStore(tmp_path)


def _load(path: Path) -> Graph:
    g = Graph()
    g.parse(data=path.read_text(encoding="utf-8"), format="json-ld")
    return g


def test_minimal_relationship_round_trips(store: ConceptStore) -> None:
    path = store.save_relationship(
        relationship_id="owns_channel",
        pref_label_ja="所有する",
        definition_ja="配信者が所有する関係",
        domain="Streamer",
        range_="Channel",
        pref_label_en=None,
        definition_en=None,
        inverse_of=None,
        scheme=None,
        extension=None,
    )

    g = _load(path)
    subj = URIRef(BASE_NS + "owns_channel")

    assert (subj, RDF.type, OWL.ObjectProperty) in g
    assert (subj, RDFS.domain, URIRef(BASE_NS + "Streamer")) in g
    assert (subj, RDFS.range, URIRef(BASE_NS + "Channel")) in g
    assert (subj, SKOS.prefLabel, Literal("所有する", lang="ja")) in g
    assert (subj, SKOS.definition, Literal("配信者が所有する関係", lang="ja")) in g


def test_inverse_and_scheme_and_multilingual(store: ConceptStore) -> None:
    path = store.save_relationship(
        relationship_id="participates_in",
        pref_label_ja="出演する",
        definition_ja="配信者が配信に出演する関係",
        domain="Streamer",
        range_="Stream",
        pref_label_en="participates in",
        definition_en="A streamer appears in a stream",
        inverse_of="features",
        scheme="VTuberDomain",
        extension=None,
    )

    g = _load(path)
    subj = URIRef(BASE_NS + "participates_in")

    assert (subj, OWL.inverseOf, URIRef(BASE_NS + "features")) in g
    assert (subj, SKOS.inScheme, URIRef(BASE_NS + "VTuberDomain")) in g
    pref_labels = set(g.objects(subj, SKOS.prefLabel))
    assert Literal("出演する", lang="ja") in pref_labels
    assert Literal("participates in", lang="en") in pref_labels


def test_dv_extension_namespace(store: ConceptStore) -> None:
    path = store.save_relationship(
        relationship_id="participates_in",
        pref_label_ja="出演する",
        definition_ja="N:M リンク",
        domain="Streamer",
        range_="Stream",
        pref_label_en=None,
        definition_en=None,
        inverse_of=None,
        scheme=None,
        extension={
            "namespace": "dv",
            "data": {"link": "LNK_COLLAB", "cardinality": "N:M"},
        },
    )

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["@context"]["dv"] == "https://metamesh.dev/ext/dv/"
    assert raw["dv:link"] == "LNK_COLLAB"
    assert raw["dv:cardinality"] == "N:M"


def test_unknown_extension_namespace_rejected(store: ConceptStore) -> None:
    with pytest.raises(ValueError, match="unknown extension namespace"):
        store.save_relationship(
            relationship_id="bogus_rel",
            pref_label_ja="x",
            definition_ja="x",
            domain="A",
            range_="B",
            pref_label_en=None,
            definition_en=None,
            inverse_of=None,
            scheme=None,
            extension={"namespace": "unknown", "data": {"x": 1}},
        )


def test_invalid_relationship_id_rejected(store: ConceptStore) -> None:
    with pytest.raises(ValueError, match="invalid relationship_id"):
        store.save_relationship(
            relationship_id="../escape",
            pref_label_ja="x",
            definition_ja="x",
            domain="A",
            range_="B",
            pref_label_en=None,
            definition_en=None,
            inverse_of=None,
            scheme=None,
            extension=None,
        )


def test_invalid_domain_rejected(store: ConceptStore) -> None:
    with pytest.raises(ValueError, match="invalid domain"):
        store.save_relationship(
            relationship_id="ok_rel",
            pref_label_ja="x",
            definition_ja="x",
            domain="../escape",
            range_="B",
            pref_label_en=None,
            definition_en=None,
            inverse_of=None,
            scheme=None,
            extension=None,
        )


def test_concept_id_validator_still_rejects_special_chars(store: ConceptStore) -> None:
    with pytest.raises(ValueError, match="invalid concept_id"):
        store.save_concept(
            concept_id="bad name!",
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


def test_relationship_multiple_extensions_coexist(store: ConceptStore) -> None:
    """Relationship 側でも DV + Kimball 共存を確認 (Issue #21)。"""
    import json
    path = store.save_relationship(
        relationship_id="participates_in_stream",
        pref_label_ja="配信に出演する",
        definition_ja="x",
        domain="Streamer",
        range_="Stream",
        pref_label_en=None,
        definition_en=None,
        inverse_of=None,
        scheme=None,
        extension=[
            {"namespace": "dv", "data": {"link": "LNK_COLLAB", "cardinality": "N:M"}},
            {"namespace": "kimball", "data": {"fact": "fct_collaboration",
                                              "fact_grain": "1 streamer × 1 stream"}},
        ],
    )
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["dv:link"] == "LNK_COLLAB"
    assert raw["dv:cardinality"] == "N:M"
    assert raw["kimball:fact"] == "fct_collaboration"
    assert raw["kimball:fact_grain"] == "1 streamer × 1 stream"
