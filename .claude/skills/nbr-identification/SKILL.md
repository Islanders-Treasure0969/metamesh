---
name: nbr-identification
description: ユーザーが metamesh オントロジー内の概念間に関係性を追加したい・概念の繋がりをモデリングしたい・ドメインエンティティの相互作用を整理したいとき、Ensemble Logical Modeling (Data Vault 系) の Natural Business Relationship (NBR) Form を模した構造化インタビューを実施し、`mcp__metamesh__add_relationship` MCP ツールで永続化する Skill。トリガー例: 「concept 間の関係性を追加したい」「Streamer と Channel を繋ぎたい」「NBR モデリング」「owns_channel みたいな関係を作りたい」。
---

# NBR (関係性) 同定インタビュー

2 つの概念の間にあるビジネス関係 1 件を構造化インタビューで聞き取り、
`owl:ObjectProperty` 形式の JSON-LD として `mcp__metamesh__add_relationship`
で永続化する Skill。

質問項目は **Ensemble Logical Modeling (Data Vault 系) の Natural Business
Relationship (NBR) Form** を下敷きにしている。狙いは、人間の頭の中に閉じ込め
られているカーディナリティ・役割ラベル・物理実装意図といったメタデータを
**下流に流れる前に明示的に抽出する** こと (PROJECT_CONTEXT.md §1.2 第①断絶点
への対処)。

この Skill は `cbc-modeling-interview` の自然な対。あちらが **ノード (concept)**
を定義する役割なら、こちらは **エッジ (relationship)** を定義する役割。

## 前提条件

- metamesh MCP server が接続済みであること。`mcp__metamesh__add_relationship`
  と `mcp__metamesh__query_concept` の両方が呼び出せれば OK。
- **両端の概念がすでに登録されていること**。`domain` / `range` が
  `mcp__metamesh__add_concept` で登録されていない concept を指していると、
  関係性ファイル自体は保存できるが、下流ツール (`generate_*` 系・衝突検出)
  で参照切れとして表面化する。先に `mcp__metamesh__query_concept` で
  存在を確認すること。

## まずディスカバリ

インタビュー本体に入る前に、状況把握から始める：

1. `mcp__metamesh__query_concept` に SPARQL `SELECT` を投げて既存概念の
   一覧を取る:
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
2. 一覧をユーザーに見せて、どの 2 概念を結びたいかを聞く。

これで「タイポや先に追加すべき概念を見落として実在しない名前で繋ごうとする」
という典型的な失敗を避けられる。

## インタビューの流れ

下表の質問を上から順番に投げる。**必須** 項目は必ず答えてもらい、**推奨/
任意** 項目はスキップ可。

| # | フィールド | 必須? | 質問 (ja) | ツール引数 |
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

### なぜ動詞より先に `domain` / `range` を聞くか

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

### DV / Kimball 拡張は任意

オントロジー自体は方法論非依存 (W3C 標準だけで完結)。DV link 名 (LNK_*)
は将来の物理実装の hint なので、未決ならスキップして OK。後から
`mcp__metamesh__add_relationship` を呼び直せば上書きできる。

## インタビュー後の流れ

1. **重複チェック (relationship_id 厳密一致)**: keyword 検索だと部分一致で
   誤検知しうる (例: "owns" で `owns_channel` / `owned_by` 両方ヒット) ため、
   IRI を直接 SPARQL ASK で照会:
   ```sparql
   PREFIX owl: <http://www.w3.org/2002/07/owl#>
   ASK { <https://metamesh.dev/ontology/owns_channel> a owl:ObjectProperty }
   ```
   `true` なら既存と被るので別 ID にするか上書きするかをユーザーに確認
2. **Endpoint 存在チェック**: `domain` と `range` が両方とも concept として
   登録済みか確認 (こちらも厳密一致の SPARQL ASK):
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

## 例

### 最小例

```text
User: 「Streamer から Channel への所有関係を追加して」

Claude: (ディスカバリ) mcp__metamesh__query_concept で Streamer / Channel の存在を確認

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

```text
User: 「Streamer と Sponsor の関係を追加したい」

Claude: (ディスカバリ) mcp__metamesh__query_concept で確認 → "Sponsor" 概念は未登録

Claude: 「Sponsor」概念がまだオントロジーに無いみたい。先に
`cbc-modeling-interview` で Sponsor を定義してから戻ってくる方が
良さそう。Sponsor をどう定義するか今聞いていい？
```

## アンチパターン

- ❌ 動詞 (relationship_id) を最初に聞く → endpoints が曖昧なまま進む
- ❌ Endpoint の存在確認をスキップ → 壊れた参照が混入
- ❌ 同じ Link を Concept と Relationship 両方に持たせる
   (Concept の `dv:link` と Relationship の `dv:link` が衝突する。
   `participates_in` と `Collaboration` の二重定義が典型例)
- ❌ Cardinality を skip するように誘導する → 後で物理設計時に詰む
- ❌ `inverse_of` を機械的に毎回聞く → 大半の関係性は逆方向を陽に定義する必要は無い (OWL の `inverseOf` は推論で十分なケースが多い)
- ❌ 関係性に「動詞 + 名詞」を詰め込む (例: `owns_channel_of_streamer`) →
   `owns_channel` で十分。domain/range が情報を持つから動詞だけで OK
