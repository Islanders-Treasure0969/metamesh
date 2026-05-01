---
name: cbc-modeling-interview
description: Use when the user wants to define a new business concept in their metamesh ontology, model their domain, or capture a piece of business vocabulary as structured metadata. Conducts a Core Business Concept (CBC) interview adapted from Ensemble Logical Modeling, then registers the result via the metamesh `add_concept` MCP tool. Triggers on phrases like "新しい概念を定義したい", "ドメインモデリングを始めたい", "X って概念を追加して", "オントロジーに entity を入れたい".
---

# CBC Modeling Interview

Captures a single business concept through a structured interview, then persists it as SKOS JSON-LD via metamesh's `add_concept` tool.

The questions are adapted from the **Core Business Concept (CBC) Form** used in Ensemble Logical Modeling (Data Vault methodology). The point is to elicit the metadata that humans usually keep in their heads — synonyms, hierarchy, intended physical implementation — *before* it gets lost downstream (PROJECT_CONTEXT.md §1.2 第①断絶点).

## Prerequisites

- The metamesh MCP server must be connected. Confirm by checking that `mcp__metamesh__add_concept` is available.
- If the ontology might already contain a similar concept, run `mcp__metamesh__query_concept` (keyword mode) first to surface duplicates / near-matches before creating a new entry.

## Interview flow

Ask the questions below in order. **Required** items must be answered; **optional** items can be skipped if the user says "skip" / "なし" / silence. Do not ask all 9 at once — go one at a time, react to the answer, and use prior answers to make follow-ups specific.

| # | Field | Required? | Question (ja) | Maps to |
|---|---|---|---|---|
| 1 | `concept_id` | ✅ | "URI として使う英語名は？(PascalCase 推奨。例: Streamer / Customer / OrderLine)" | tool arg `concept_id` |
| 2 | `pref_label_ja` | ✅ | "日本語での正式名称は？(例: 配信者)" | `pref_label_ja` |
| 3 | `definition_ja` | ✅ | "1〜2 文で何を表す概念か説明してください" | `definition_ja` |
| 4 | `pref_label_en` | 推奨 | "英語での正式名称は？(skip 可)" | `pref_label_en` |
| 5 | `definition_en` | 推奨 | "英訳の定義文があれば教えてください (skip 可)" | `definition_en` |
| 6 | `alt_labels_ja` / `alt_labels_en` | 推奨 | "他に呼ばれる名前は？(別表記・略称・英訳・社内用語など全部)" | `alt_labels_ja`, `alt_labels_en` |
| 7 | `broader` / `narrower` / `related` | 任意 | "上位概念・下位概念・関連概念があれば教えてください" | `broader`, `narrower`, `related` |
| 8 | `extension` (DV/Kimball) | 任意 | "Data Vault で実装するなら Hub？Link？business_key になる属性は？(Kimball なら Dimension/Fact、SCD Type)" | `extension={namespace, data}` |
| 9 | `scheme` | 任意 | "所属する Concept Scheme があれば (例: VTuberDomain)" | `scheme` |

### Why ask in BOTH languages

英訳・別表記・社内用語の差分は **§1.3 で挙げた「同義語が AI に届かない」問題の元凶**。「得意先」「顧客」「Customer」「Account」が同じ概念だと AI が知らないと、そもそも検索クエリが合致しない。alt_labels は雑にでも全部入れる価値がある。

### Why DV/Kimball metadata is optional

オントロジー自体は方法論非依存 (W3C 標準だけで完結) が原則 (PROJECT_CONTEXT.md §2.2)。DV/Kimball 拡張は「将来の物理実装の hint」として残すもので、まだ決まってないなら skip してよい。後から `add_concept` を呼び直せば上書きできる。

## After the interview

1. **重複チェック**: 入力された `concept_id` と類似する既存概念がないか `mcp__metamesh__query_concept` で確認 (keyword モードで concept_id と pref_label_ja を投げる)
2. **登録**: `mcp__metamesh__add_concept` を呼ぶ。引数は会話で集めた値をそのまま渡す
3. **確認**: 保存されたファイルパスをユーザーに見せる (例: `Saved: /path/to/ontology/concepts/Streamer.jsonld`)
4. **次の一手**: 関係性 (NBR) もモデリングするか聞く。YES なら `nbr-identification` Skill を案内 (まだ無ければ「次は `add_relationship` で繋いでいきましょう」とだけ言う)

## Examples

### Minimal example

```text
User: 「Streamer って概念を追加して」

Claude: (Q1) URI として使う英語名は？
User: Streamer

Claude: (Q2) 日本語での正式名称は？
User: 配信者

Claude: (Q3) 1〜2 文で何を表す概念か説明してください
User: VTuber 個人を表す概念

[Q4-9: skip]

Claude: → mcp__metamesh__add_concept(
  concept_id="Streamer",
  pref_label_ja="配信者",
  definition_ja="VTuber 個人を表す概念"
)
→ Saved: ontology/concepts/Streamer.jsonld
```

### Full example with DV mapping

```text
User: 「コラボの概念を作りたい」

Claude: (重複チェック) "コラボ" で query_concept → 既存 0 件
(Q1-9) を会話で順に
→ mcp__metamesh__add_concept(
  concept_id="Collaboration",
  pref_label_ja="コラボ",
  pref_label_en="Collaboration",
  definition_ja="複数の配信者が同時に出演する配信イベント",
  alt_labels_ja=["コラボ配信", "合同配信"],
  alt_labels_en=["Collab", "Joint Stream"],
  related=["Streamer", "Stream"],
  scheme="VTuberDomain",
  extension={"namespace": "dv", "data": {"link": "LNK_COLLAB", "cardinality": "N:M"}}
)
```

## Anti-patterns

- ❌ 9 個の質問を 1 メッセージで投げない (圧迫感、答える気を削ぐ)
- ❌ 既存類似概念を確認せずに新規作成する (オントロジーの分裂)
- ❌ alt_labels をスキップする (これがある/ないでオントロジーの実用性が大きく変わる)
- ❌ DV/Kimball 拡張を強制する (方法論固有の hint、未決でよい)
- ❌ 概念を保存後に何もアナウンスしない (ファイルパスを見せて、次の一手を提示する)
