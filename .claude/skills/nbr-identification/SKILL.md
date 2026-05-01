---
name: nbr-identification
description: Use when the user wants to add a relationship between business concepts in their metamesh ontology, model how concepts connect, or identify how their domain entities interact. Conducts a Natural Business Relationship (NBR) interview adapted from Ensemble Logical Modeling, then registers the result via the metamesh `add_relationship` MCP tool. Triggers on phrases like "concept 間の関係性を追加したい", "Streamer と Channel を繋ぎたい", "NBR モデリング", "owns_channel みたいな関係を作りたい".
---

# NBR Identification Interview

Captures a single business relationship between two concepts through a
structured interview, then persists it as `owl:ObjectProperty` JSON-LD via
metamesh's `add_relationship` tool.

The questions are adapted from the **Natural Business Relationship (NBR)
Form** used in Ensemble Logical Modeling (Data Vault methodology). The
point is to elicit the metadata that humans usually keep in their heads —
cardinality, role labels, intended physical implementation — *before* it
gets lost downstream (PROJECT_CONTEXT.md §1.2 第①断絶点).

This Skill is the natural complement to `cbc-modeling-interview`: that one
defines the nodes (concepts), this one defines the edges (relationships).

## Prerequisites

- The metamesh MCP server must be connected. Confirm by checking that
  `mcp__metamesh__add_relationship` and `mcp__metamesh__query_concept` are
  both available.
- **Both endpoints must already exist as concepts.** If `domain` or
  `range` references a concept that hasn't been added via `add_concept`,
  the relationship will technically save but downstream tools (`generate_*`,
  collision detection) will surface broken references. Run
  `mcp__metamesh__query_concept` first to confirm presence.

## Discovery first

Before launching into the interview, get oriented:

1. Call `mcp__metamesh__query_concept` with a SPARQL `SELECT` to list all
   existing concepts:
   ```sparql
   PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
   SELECT ?id ?label WHERE {
       ?c a skos:Concept ;
          skos:prefLabel ?label .
       BIND(STRAFTER(STR(?c), "/ontology/") AS ?id)
       FILTER(LANG(?label) = "ja")
   }
   ORDER BY ?id
   ```
2. Show the user the list and ask which two concepts they want to relate.

This avoids the common failure mode where the user names a concept that
doesn't exist yet (typo, or they meant to add it first).

## Interview flow

Ask the questions below in order. **Required** items must be answered;
**optional** items can be skipped.

| # | Field | Required? | Question (ja) | Maps to |
|---|---|---|---|---|
| 1 | `domain` | ✅ | "主語側の概念は？(例: Streamer)" | `domain` |
| 2 | `range` | ✅ | "目的語側の概念は？(例: Channel)" | `range` |
| 3 | `relationship_id` | ✅ | "関係を表す英語の述語は？(lower_snake_case 推奨。例: owns_channel / participates_in)" | `relationship_id` |
| 4 | `pref_label_ja` | ✅ | "日本語での動詞表現は？(例: チャンネルを所有する)" | `pref_label_ja` |
| 5 | `definition_ja` | ✅ | "1〜2 文で何を表す関係か説明してください" | `definition_ja` |
| 6 | `pref_label_en` | 推奨 | "英語での動詞表現は？(例: owns channel)" | `pref_label_en` |
| 7 | `definition_en` | 推奨 | "英訳の定義文があれば" | `definition_en` |
| 8 | `cardinality` | 推奨 | "カーディナリティは？(1:1 / 1:N / N:1 / N:M)" | `extension.data.cardinality` |
| 9 | `inverse_of` | 任意 | "逆方向の関係性 ID があれば (例: owns_channel ↔ owned_by)" | `inverse_of` |
| 10 | DV link | 任意 | "Data Vault 実装する場合の Link 名 (例: LNK_STREAMER_CHANNEL)" | `extension.data.link` |
| 11 | DV role attribute | 任意 | "Link に役割属性 (role) を持たせる必要があれば (例: participant_role: owner / guest)" | `extension.data.role_attribute` |
| 12 | `scheme` | 任意 | "所属 Concept Scheme があれば (例: VTuberDomain)" | `scheme` |

### Why ask `domain` / `range` BEFORE the verb

NBR の典型的な失敗パターンは **「動詞だけ先に決めて、何と何を繋ぐかが曖昧」** な状態。
"participates" って言われても、「誰が何に participate するの？」が無いと情報量ゼロ。
先に endpoints を fix すると、自然に動詞表現も決まりやすい (Streamer × Stream → "出演する")。

### Cardinality の聞き方

カーディナリティは **「主語側から目的語側を見たときの個数」+ 「目的語側から主語側を見たときの個数」** の組み合わせ。

- **1:1** — 1 つの A が 1 つの B にだけ関係する (例: Person owns Passport)
- **1:N** — 1 つの A が複数の B に関係する (例: Streamer owns Channel)
- **N:1** — 複数の A が 1 つの B に関係する (= 1:N の逆視点)
- **N:M** — 多対多 (例: Streamer participates_in Stream)

「N:M なら DV 的には Link テーブル必須」「1:N なら片側 Hub の Sat に持たせる
こともできる」等の含意があるので、できれば聞いておく。

### DV / Kimball 拡張は optional

オントロジー自体は方法論非依存 (W3C 標準だけで完結)。DV link 名 (LNK_*)
は将来の物理実装の hint なので、未決ならスキップして OK。後から
`add_relationship` を呼び直せば上書きできる。

## After the interview

1. **重複チェック**: `relationship_id` で `mcp__metamesh__query_concept`
   (keyword モード) を投げて既存被りが無いか確認
2. **Endpoint 存在チェック**: `domain` と `range` が両方とも concept として
   登録済みか確認 (`query_concept` で SPARQL ASK が便利):
   ```sparql
   PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
   ASK {
       <https://metamesh.dev/ontology/Streamer> a skos:Concept .
       <https://metamesh.dev/ontology/Channel> a skos:Concept .
   }
   ```
   `false` なら、先に `cbc-modeling-interview` で不足概念を追加するよう案内
3. **登録**: `mcp__metamesh__add_relationship` を呼ぶ
4. **確認**: 保存されたファイルパスをユーザーに見せる
5. **次の一手**: 逆関係 (`inverse_of`) も登録するか聞く。あるいは「他の概念
   ペアも繋ぎますか？」と続ける

## Examples

### 最小例

```
User: 「Streamer から Channel への所有関係を追加して」

Claude: (Discovery) query_concept で Streamer / Channel の存在を確認

(Q1) domain は Streamer で良いですね？
User: yes

(Q2) range は Channel で良いですね？
User: yes

(Q3) 関係の英語表現は？
User: owns_channel

(Q4) 日本語表現は？
User: チャンネルを所有する

(Q5) 定義は？
User: 配信者がチャンネルを所有する関係

(Q8) カーディナリティは？
User: 1:N

[Q6, Q7, Q9-12: skip]

Claude: → mcp__metamesh__add_relationship(
  relationship_id="owns_channel",
  pref_label_ja="チャンネルを所有する",
  definition_ja="配信者がチャンネルを所有する関係",
  domain="Streamer",
  range="Channel",
  extension={"namespace": "dv", "data": {"cardinality": "1:N"}}
)
→ Saved: ontology/relationships/owns_channel.jsonld
```

### Endpoint 不在のリカバリ

```
User: 「Streamer と Sponsor の関係を追加したい」

Claude: (Discovery) query_concept で確認 → "Sponsor" 概念は未登録

Claude: 「Sponsor」概念がまだオントロジーに無いみたい。先に
`cbc-modeling-interview` で Sponsor を定義してから戻ってくる方が
良さそう。Sponsor をどう定義するか今聞いていい？
```

## Anti-patterns

- ❌ 動詞 (relationship_id) を最初に聞く → endpoints が曖昧なまま進む
- ❌ Endpoint の存在確認をスキップ → 壊れた参照が混入
- ❌ 同じ Link を Concept と Relationship 両方に持たせる
   (Concept の `dv:link` と Relationship の `dv:link` が衝突する。
   `participates_in` と `Collaboration` の二重定義が典型例)
- ❌ Cardinality を skip するように誘導する → 後で物理設計時に詰む
- ❌ `inverse_of` を機械的に毎回聞く → 大半の関係性は逆方向を陽に定義する必要は無い (OWL の `inverseOf` は推論で十分なケースが多い)
- ❌ 関係性に「動詞 + 名詞」を詰め込む (例: `owns_channel_of_streamer`) →
   `owns_channel` で十分。domain/range が情報を持つから動詞だけで OK
