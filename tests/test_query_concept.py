"""query_concept (keyword + sparql) の動作検証。"""
from __future__ import annotations

from pathlib import Path

import pytest

from metamesh.ontology.store import ConceptStore
from metamesh.queries.concept import keyword_search, sparql_query


@pytest.fixture
def populated_root(tmp_path: Path) -> Path:
    store = ConceptStore(tmp_path)
    store.save_concept(
        concept_id="Streamer",
        pref_label_ja="配信者",
        definition_ja="VTuber 個人を表す概念。バーチャルアバターを使って配信を行う。",
        pref_label_en="Streamer",
        definition_en="A VTuber individual.",
        alt_labels_ja=["VTuber", "ライバー"],
        alt_labels_en=["Talent"],
        broader=None,
        narrower=[],
        related=[],
        scheme="VTuberDomain",
        extension={"namespace": "dv", "data": {"hub": "HUB_STREAMER", "business_key": "streamer_id"}},
    )
    store.save_concept(
        concept_id="Customer",
        pref_label_ja="顧客",
        definition_ja="商品を購入する主体。",
        pref_label_en="Customer",
        definition_en=None,
        alt_labels_ja=["得意先", "お客様"],
        alt_labels_en=["Account"],
        broader=None,
        narrower=[],
        related=[],
        scheme=None,
        extension={"namespace": "dv", "data": {"hub": "HUB_CUSTOMER"}},
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
        extension=None,
    )
    store.save_relationship(
        relationship_id="owns_channel",
        pref_label_ja="チャンネルを所有する",
        definition_ja="配信者がチャンネルを所有する関係",
        domain="Streamer",
        range_="Channel",
        pref_label_en=None,
        definition_en=None,
        inverse_of=None,
        scheme=None,
        extension={"namespace": "dv", "data": {"link": "LNK_STREAMER_CHANNEL", "cardinality": "1:N"}},
    )
    return tmp_path


# ---------- keyword search ----------


def test_keyword_matches_id_case_insensitive(populated_root: Path) -> None:
    res = keyword_search(ontology_root=populated_root, keyword="streamer")
    ids = {m["id"] for m in res["matches"]}
    assert "Streamer" in ids


def test_keyword_matches_alt_label_in_japanese(populated_root: Path) -> None:
    """The signature 'synonym discovery' use case from §1.3."""
    res = keyword_search(ontology_root=populated_root, keyword="得意先")
    assert res["count"] == 1
    m = res["matches"][0]
    assert m["id"] == "Customer"
    assert any(f["field"] == "skos:altLabel@ja" and f["value"] == "得意先" for f in m["matched_fields"])


def test_keyword_matches_alt_label_english(populated_root: Path) -> None:
    res = keyword_search(ontology_root=populated_root, keyword="vtuber")
    ids = {m["id"] for m in res["matches"]}
    # VTuber matches Streamer (alt label) AND Streamer's definition / pref label en
    assert "Streamer" in ids


def test_keyword_matches_definition_with_snippet(populated_root: Path) -> None:
    res = keyword_search(ontology_root=populated_root, keyword="バーチャルアバター")
    streamer = next(m for m in res["matches"] if m["id"] == "Streamer")
    def_match = next(
        f for f in streamer["matched_fields"] if f["field"] == "skos:definition@ja"
    )
    assert "バーチャルアバター" in def_match["value"]


def test_keyword_matches_relationship(populated_root: Path) -> None:
    res = keyword_search(ontology_root=populated_root, keyword="owns_channel")
    assert any(m["id"] == "owns_channel" and m["type"] == "relationship" for m in res["matches"])


def test_keyword_one_entry_per_doc_even_when_multiple_fields_match(populated_root: Path) -> None:
    """Streamer matches in @id, prefLabel@en, altLabel@en (VTuber), definition@ja - all of them."""
    res = keyword_search(ontology_root=populated_root, keyword="streamer")
    streamer_entries = [m for m in res["matches"] if m["id"] == "Streamer"]
    assert len(streamer_entries) == 1
    # But matched_fields should list multiple
    assert len(streamer_entries[0]["matched_fields"]) >= 2


def test_keyword_limit_truncates(populated_root: Path) -> None:
    # All 3 concepts and 1 rel are in VTuberDomain or similar; pick a wide-net keyword
    # 'a' matches many things (Streamer, Talent, A...) but lowercase
    res = keyword_search(ontology_root=populated_root, keyword="a", limit=2)
    assert res["count"] == 2
    assert res["truncated"] is True


def test_keyword_no_match_returns_empty(populated_root: Path) -> None:
    res = keyword_search(ontology_root=populated_root, keyword="xyzzy_no_such_thing")
    assert res["count"] == 0
    assert res["matches"] == []
    assert res["truncated"] is False


def test_keyword_empty_string_rejected(populated_root: Path) -> None:
    with pytest.raises(ValueError, match="non-empty"):
        keyword_search(ontology_root=populated_root, keyword="")


# ---------- SPARQL ----------


def test_sparql_select_all_concepts(populated_root: Path) -> None:
    res = sparql_query(
        ontology_root=populated_root,
        sparql="""
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        SELECT ?c WHERE { ?c a skos:Concept }
        """,
    )
    assert res["mode"] == "sparql"
    assert res["columns"] == ["c"]
    # 3 concepts in the fixture
    assert res["count"] == 3
    ids = {row[0].rsplit("/", 1)[-1] for row in res["rows"]}
    assert ids == {"Streamer", "Customer", "Channel"}


def test_sparql_filter_by_dv_hub(populated_root: Path) -> None:
    """Find concepts that bind to a DV Hub - the most useful structured query."""
    res = sparql_query(
        ontology_root=populated_root,
        sparql="""
        PREFIX dv: <https://metamesh.dev/ext/dv/>
        SELECT ?c ?hub WHERE { ?c dv:hub ?hub }
        """,
    )
    assert res["count"] == 2  # Streamer, Customer (Channel has no dv extension)
    hubs = {row[1] for row in res["rows"]}
    assert hubs == {"HUB_STREAMER", "HUB_CUSTOMER"}


def test_sparql_relationship_domain_range(populated_root: Path) -> None:
    res = sparql_query(
        ontology_root=populated_root,
        sparql="""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        SELECT ?rel ?domain ?range WHERE {
            ?rel a owl:ObjectProperty ;
                 rdfs:domain ?domain ;
                 rdfs:range ?range .
        }
        """,
    )
    assert res["count"] == 1
    assert res["rows"][0][0].endswith("/owns_channel")
    assert res["rows"][0][1].endswith("/Streamer")
    assert res["rows"][0][2].endswith("/Channel")


def test_sparql_limit_truncates(populated_root: Path) -> None:
    res = sparql_query(
        ontology_root=populated_root,
        sparql="""
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        SELECT ?c WHERE { ?c a skos:Concept }
        """,
        limit=1,
    )
    assert res["count"] == 1
    assert res["truncated"] is True


def test_sparql_empty_string_rejected(populated_root: Path) -> None:
    with pytest.raises(ValueError, match="non-empty"):
        sparql_query(ontology_root=populated_root, sparql="")


def test_sparql_whitespace_only_rejected(populated_root: Path) -> None:
    with pytest.raises(ValueError, match="non-empty"):
        sparql_query(ontology_root=populated_root, sparql="   \n  ")


def test_sparql_select_response_includes_type_field(populated_root: Path) -> None:
    res = sparql_query(
        ontology_root=populated_root,
        sparql="""
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        SELECT ?c WHERE { ?c a skos:Concept } LIMIT 1
        """,
    )
    assert res["type"] == "SELECT"


def test_sparql_construct_returns_triples(populated_root: Path) -> None:
    """CONSTRUCT used by Skills to fetch a subgraph (e.g. neighborhood) for rendering."""
    res = sparql_query(
        ontology_root=populated_root,
        sparql="""
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        CONSTRUCT { ?c skos:prefLabel ?l }
        WHERE { ?c skos:prefLabel ?l . FILTER(LANG(?l) = "ja") }
        """,
    )
    assert res["mode"] == "sparql"
    assert res["type"] == "CONSTRUCT"
    assert "triples" in res
    assert "rows" not in res
    # 3 concepts + 1 relationship in fixture, all with ja prefLabel
    assert res["count"] == 4
    # Each triple is [s, p, o] strings
    for triple in res["triples"]:
        assert len(triple) == 3
        assert all(isinstance(t, str) for t in triple)


def test_sparql_describe_returns_triples(populated_root: Path) -> None:
    res = sparql_query(
        ontology_root=populated_root,
        sparql="DESCRIBE <https://metamesh.dev/ontology/Streamer>",
    )
    assert res["type"] == "DESCRIBE"
    assert "triples" in res
    # Streamer has many properties (labels, definition, alt labels, dv:*, etc.)
    assert res["count"] > 5


def test_sparql_construct_limit_truncates(populated_root: Path) -> None:
    res = sparql_query(
        ontology_root=populated_root,
        sparql="""
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        CONSTRUCT { ?c skos:prefLabel ?l }
        WHERE { ?c skos:prefLabel ?l }
        """,
        limit=2,
    )
    assert res["count"] == 2
    assert res["truncated"] is True


def test_sparql_ask_returns_boolean_true(populated_root: Path) -> None:
    res = sparql_query(
        ontology_root=populated_root,
        sparql="""
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        ASK { <https://metamesh.dev/ontology/Streamer> a skos:Concept }
        """,
    )
    assert res["type"] == "ASK"
    assert res["boolean"] is True
    assert "triples" not in res
    assert "rows" not in res


def test_sparql_ask_returns_boolean_false(populated_root: Path) -> None:
    res = sparql_query(
        ontology_root=populated_root,
        sparql="""
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        ASK { <https://metamesh.dev/ontology/NonExistent> a skos:Concept }
        """,
    )
    assert res["type"] == "ASK"
    assert res["boolean"] is False
