"""export_llm_context の動作検証。

Markdown 文字列の構造を直接 assert すると改行差異に脆くなるので、
代表的な substring (ID, label, definition, dv mapping 等) の含有のみ検証する。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from metamesh.generators.llm_context import export_llm_context
from metamesh.ontology.store import ConceptStore


@pytest.fixture
def populated_root(tmp_path: Path) -> Path:
    store = ConceptStore(tmp_path)
    store.save_concept(
        concept_id="Streamer",
        pref_label_ja="配信者",
        definition_ja="VTuber 個人を表す概念。",
        pref_label_en="Streamer",
        definition_en="A VTuber individual.",
        alt_labels_ja=["VTuber", "ライバー"],
        alt_labels_en=["Talent"],
        broader=None,
        narrower=["HololiveStreamer"],
        related=["Channel"],
        scheme="VTuberDomain",
        extension={"namespace": "dv", "data": {"hub": "HUB_STREAMER", "business_key": "streamer_id"}},
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
        inverse_of="owned_by",
        scheme="VTuberDomain",
        extension={"namespace": "dv", "data": {"link": "LNK_STREAMER_CHANNEL", "cardinality": "1:N"}},
    )
    return tmp_path


def test_h1_title_default(populated_root: Path) -> None:
    md = export_llm_context(ontology_root=populated_root)
    assert md.startswith("# metamesh ontology context")


def test_h1_title_custom(populated_root: Path) -> None:
    md = export_llm_context(ontology_root=populated_root, title="VTuber Domain")
    assert md.startswith("# VTuber Domain")


def test_summary_counts_in_header(populated_root: Path) -> None:
    md = export_llm_context(ontology_root=populated_root)
    assert "2 concepts" in md
    assert "1 relationships" in md


def test_concepts_summary_table_lists_all_concepts(populated_root: Path) -> None:
    md = export_llm_context(ontology_root=populated_root)
    # Both ids appear in the summary table
    assert "| `Streamer` |" in md
    assert "| `Channel` |" in md


def test_relationships_summary_table_lists_all_relationships(populated_root: Path) -> None:
    md = export_llm_context(ontology_root=populated_root)
    assert "| `owns_channel` |" in md
    # Domain / range / cardinality rendered
    assert "`Streamer`" in md
    assert "`Channel`" in md
    assert "1:N" in md


def test_concept_section_renders_definition_and_synonyms(populated_root: Path) -> None:
    md = export_llm_context(ontology_root=populated_root)
    assert "### `Streamer` — 配信者 / Streamer" in md
    assert "VTuber 個人を表す概念。" in md
    assert "_A VTuber individual._" in md
    assert "**Synonyms:**" in md
    assert "VTuber, ライバー" in md
    assert "Talent" in md


def test_concept_section_renders_ontology_links(populated_root: Path) -> None:
    md = export_llm_context(ontology_root=populated_root)
    assert "narrower: `HololiveStreamer`" in md
    assert "related: `Channel`" in md


def test_concept_section_renders_dv_mapping(populated_root: Path) -> None:
    md = export_llm_context(ontology_root=populated_root)
    assert "**DV implementation:**" in md
    assert "`hub`: HUB_STREAMER" in md
    assert "`business_key`: streamer_id" in md


def test_concept_section_renders_scheme(populated_root: Path) -> None:
    md = export_llm_context(ontology_root=populated_root)
    assert "_Scheme: `VTuberDomain`_" in md


def test_concept_without_optional_fields_renders_minimally(populated_root: Path) -> None:
    md = export_llm_context(ontology_root=populated_root)
    # Channel has no en label, no synonyms, no dv extension
    assert "### `Channel` — チャンネル" in md
    assert "配信枠。" in md
    # No extra noise sections for Channel
    # (Cannot easily assert absence in a single string, so we check the section
    # doesn't claim DV implementation)
    channel_section_start = md.index("### `Channel`")
    next_section = md.find("### `", channel_section_start + 1)
    channel_block = md[channel_section_start:next_section if next_section != -1 else None]
    assert "DV implementation" not in channel_block
    assert "Synonyms" not in channel_block


def test_relationship_section_renders_arrow_and_inverse(populated_root: Path) -> None:
    md = export_llm_context(ontology_root=populated_root)
    assert "### `owns_channel` — チャンネルを所有する / owns channel" in md
    assert "`Streamer` → `Channel`" in md
    assert "(1:N)" in md
    assert "**Inverse of:** `owned_by`" in md


def test_relationship_section_renders_dv_link(populated_root: Path) -> None:
    md = export_llm_context(ontology_root=populated_root)
    assert "`link`: LNK_STREAMER_CHANNEL" in md
    assert "`cardinality`: 1:N" in md


def test_empty_ontology_produces_minimal_valid_markdown(tmp_path: Path) -> None:
    (tmp_path / "concepts").mkdir()
    (tmp_path / "relationships").mkdir()
    md = export_llm_context(ontology_root=tmp_path)
    assert md.startswith("# metamesh ontology context")
    assert "0 concepts" in md
    assert "0 relationships" in md
    # No section headers when there's no content
    assert "## Concepts" not in md
    assert "## Relationships" not in md


def test_kimball_extension_renders_too(tmp_path: Path) -> None:
    store = ConceptStore(tmp_path)
    store.save_concept(
        concept_id="Customer",
        pref_label_ja="顧客",
        definition_ja="x",
        pref_label_en=None,
        definition_en=None,
        alt_labels_ja=[],
        alt_labels_en=[],
        broader=None,
        narrower=[],
        related=[],
        scheme=None,
        extension={"namespace": "kimball", "data": {"dimension": "dim_customer", "scd_type": 2}},
    )
    md = export_llm_context(ontology_root=tmp_path)
    assert "**Kimball implementation:**" in md
    assert "`dimension`: dim_customer" in md
    assert "`scd_type`: 2" in md


def test_list_value_in_extension_rendered_as_csv(tmp_path: Path) -> None:
    store = ConceptStore(tmp_path)
    store.save_relationship(
        relationship_id="participates_in",
        pref_label_ja="出演",
        definition_ja="x",
        domain="A",
        range_="B",
        pref_label_en=None,
        definition_en=None,
        inverse_of=None,
        scheme=None,
        extension={"namespace": "dv", "data": {"link": "LNK_X", "participants": ["HUB_A", "HUB_B"]}},
    )
    md = export_llm_context(ontology_root=tmp_path)
    assert "`participants`: HUB_A, HUB_B" in md
