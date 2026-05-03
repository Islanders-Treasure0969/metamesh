---
name: beam-modeling-interview
description: ユーザーがビジネスイベント (注文・配信・取引・コラボ等) を Star Schema で分析できるよう設計したい・Fact テーブルを設計したい・BEAM (Business Event Analysis & Modeling) でモデリングしたいとき、Lawrence Corr "Agile Data Warehouse Design" の 7Ws (Who/What/When/Where/How many/Why/How) フレームワークで構造化インタビューを実施し、`mcp__metamesh__add_concept` 系 MCP ツールで SKOS Concept として登録する Skill。`cbc-modeling-interview` の Kimball 系対称版。トリガー例: 「BEAM でモデリングしたい」「ファクトテーブルを設計したい」「7Ws で配信イベントを整理したい」「Star Schema 用に分析イベントを定義」。
---

# BEAM (7Ws) Modeling Interview

ビジネスイベント 1 件を 7Ws フレームワークで構造化インタビューし、
`mcp__metamesh__add_concept` / `add_relationship` で SKOS / OWL JSON-LD として
永続化する Skill。`kimball:` 拡張に Dim/Fact 候補を記録する。

質問項目は **Lawrence Corr & Jim Stagnitto _Agile Data Warehouse Design_
(2011) の BEAM (Business Event Analysis & Modeling) Form** を下敷きに
している。狙いは、業務担当者と DE が同じ部屋でイベントを引き出すワーク
ショップ (Model Storming) を Claude が代行し、Star Schema 設計の出発点
となる **Fact + 周辺 Dimension のスケルトン** をオントロジーに落とすこと。

この Skill は `cbc-modeling-interview` の Kimball 系対称。あちらが
**エンティティの identity** を引き出すのに対し、こちらは
**イベントの measurement** を引き出す。

## 前提条件

- metamesh MCP server が接続済み (`mcp__metamesh__add_concept` /
  `add_relationship` / `query_concept` の 3 つが必要)
- 7Ws の Who / What 列に登場する **エンティティ系 Concept** は、可能なら
  事前に `cbc-modeling-interview` で登録済みであることが望ましい (理由は
  下記「ディスカバリ → 再利用」参照)

### ⚠️ 既知の制約

`add_concept` は extension を **1 namespace/呼び出し** しか受け付けない
([Issue #21](https://github.com/Islanders-Treasure0969/metamesh/issues/21))。
そのため、**既に `dv:hub` 等の DV 拡張を持つ Concept に `kimball:` 拡張を
追加で書く** ことは現状できない (上書きで dv: が消える)。

対処:

| 状況 | 対処 |
|---|---|
| Concept が新規 (extension まだ無し) | そのまま `add_concept` で `kimball:` を書く |
| Concept が DV 専用 (dv: あり, kimball: 無し) | **対象 .jsonld を直接 git diff で確認** しながら手編集して `kimball:dimension` 等を追記。または #21 の修正を待つ |
| Concept が Kimball 専用 (dv: 無し, kimball: あり) | そのまま `add_concept` で上書き再登録 |

新規プロジェクトでは「先に BEAM で Kimball 拡張を書き、後で DV 拡張を
追加する場合は同様の手編集 / #21 待ち」になる。

## ディスカバリ → 再利用 (Modeling Storming 継続性)

BEAM セッションの典型的な失敗は **「Who? What? の議論に時間を取られて
measurement (How many) の議論ができない」** こと。CBC で既に Concept が
固まっていれば、BEAM では既存 Concept を選ぶだけで済む。

インタビュー本体に入る前に必ずディスカバリ:

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

この一覧を見せて「Who/What はこの中から選ぶか、新規が必要か」を最初に
確認する。新規が必要なら **`cbc-modeling-interview` Skill を案内**して
そちらで先に登録 (戻ってきて BEAM 続行)。

## インタビューの流れ (7Ws)

下表の順で投げる。`cardinality` (How many) と `measure` 系は **必須**、
それ以外は推奨/任意。

| W | 必須? | 質問 (ja) | Star Schema での役割 |
|---|---|---|---|
| 1. **What** | ✅ | "何のイベント? (例: 配信開始, 注文確定, コラボ実施)" | Fact テーブル名 (`fct_<verb>`) |
| 2. **Who** | ✅ | "誰が関わる? (主体・受け手・第三者) - 既存 Concept から選ぶか?" | 主要 Dimension (`dim_streamer` 等) |
| 3. **What (object)** | ✅ | "何が対象? (商品・配信・楽曲)" | Dimension (`dim_stream` 等) |
| 4. **When** | ✅ | "いつ起きる? (粒度: 秒/分/日)" | `dim_date` / `dim_time` (Conformed) |
| 5. **Where** | 推奨 | "どこで起きる? (場所・チャネル・地理)" | Dimension (`dim_location` 等) |
| 6. **How many** | ✅ | "数量・金額・件数は? (= Fact の measure)" | **Fact の measure 列** |
| 7. **Why** | 推奨 | "理由・原因・キャンペーン?" | Dimension or **degenerate** |
| 8. **How** | 推奨 | "手段・方法・チャネル種別?" | Dimension (`dim_method` 等) |
| 9. **fact_grain** | ✅ | "Fact 1 行は何を表す? (例: 1 streamer × 1 stream 出演)" | grain 文書化 |
| 10. **scd_type** (Dim ごと) | 推奨 | "各 Dimension の履歴管理は? (Type 1/2/3)" | SCD Type |

### 質問の出し方

- 1〜10 を **1 メッセージで束ねない**。1 問ずつ、回答に応じて follow-up を
  具体化する
- Who / What (object) で既存 Concept が選ばれたら、その Concept の
  `pref_label` と `definition` を提示して "これで合ってる?" と確認
- Where / Why / How で skip の合図 (「特になし」「skip」) があれば
  即座に次へ

### 「How many」 (measure) の聞き出し方

ここが BEAM の核心。以下のサブ質問を順に:

1. 数えるか?  (count / sum / avg)
2. 単位は? (件・円・分・人)
3. additive か? (足し算が意味を持つ → fully additive。途中状態だけ意味
   を持つ → semi-additive、足せない → non-additive)
4. 派生 measure はあるか? (例: `unit_price * quantity = revenue`)

例:
- `collab_count` (additive, 件)
- `duration_minutes` (additive, 分)
- `concurrent_viewers_avg` (semi-additive, 人; 平均は足せない)

## インタビュー後の流れ

1. **Fact 用の relationship 登録**

   イベント (Fact) は概念間の関係性として表現する。`add_relationship` で:

   ```python
   mcp__metamesh__add_relationship(
       relationship_id="participates_in_stream",  # 例
       pref_label_ja="配信に出演する",
       definition_ja="配信者が配信に出演するイベント...",
       domain="Streamer",
       range_="Stream",
       extension={"namespace": "kimball", "data": {
           "fact": "fct_collaboration",
           "fact_grain": "1 streamer × 1 stream の出演",
           "measures": ["collab_count", "duration_minutes"],
           "fact_type": "transaction"  # transaction / periodic_snapshot / accumulating_snapshot
       }}
   )
   ```

2. **Dimension マーキング (新規 Concept のみ)**

   Who / What (object) / Where / Why / How で **新規** Concept が必要に
   なった場合のみ:

   ```python
   mcp__metamesh__add_concept(
       concept_id="PaymentMethod",
       pref_label_ja="決済方法",
       definition_ja="...",
       extension={"namespace": "kimball", "data": {
           "dimension": "dim_payment_method",
           "scd_type": 1
       }}
   )
   ```

3. **既存 Concept への Kimball 拡張追加 (現状制約あり)**

   既存 Concept (`Streamer` 等) に Kimball 拡張を追加する場合は、
   上記「⚠️ 既知の制約」を読んで対処を選ぶ。

4. **登録結果のサマリ表示**

   生成された Fact relationship + 関連 Dimension Concept のリスト、
   各保存先パスをユーザーに見せる。

5. **次の一手**

   - 同じ業務領域に他のイベントもあれば、続けて BEAM 実施
   - 全イベント整理が終わったら `dimension-fact-identification` Skill
     ([Issue #19](https://github.com/Islanders-Treasure0969/metamesh/issues/19))
     で Conformed Dimension を診断
   - 物理設計に進むなら `star-schema-design` Skill
     ([Issue #20](https://github.com/Islanders-Treasure0969/metamesh/issues/20))

## 例

### 例 1: 配信イベントの最小 BEAM

```text
User: 「コラボ配信のイベントを BEAM で整理したい」

Claude: (ディスカバリ) mcp__metamesh__query_concept で既存一覧
        → Streamer / Channel / Stream / Organization / ... 全 7 件あり

Claude: (Q1 What) 何のイベントですか?
User: コラボ配信が行われた、というイベント

Claude: (Q2 Who) 既存 Concept から「Streamer」が主体で良い? 複数 streamer が関わるなら N:M。
User: yes、Streamer が N:M で

Claude: (Q3 What-object) 配信そのものは「Stream」概念で良い?
User: yes

Claude: (Q4 When) 粒度は分単位? 秒単位?
User: 分単位で十分 (start_scheduled の精度に合わせる)

Claude: (Q5 Where) 場所概念は? 既存にチャネルあり、それを使う?
User: Channel を使う

Claude: (Q6 How many) measure は? まず数を聞かせて。
User: コラボ件数 (1)、配信長 (分)、ピーク同時視聴者数

Claude: (How many follow-up) ピーク同時視聴者は semi-additive (平均にしか
        意味なし、足し算しちゃダメ) で良い?
User: yes

Claude: (Q9 grain) Fact 1 行は「1 streamer × 1 stream の出演」で OK?
User: OK

[Q7 Why, Q8 How: skip]

Claude: → mcp__metamesh__add_relationship(
  relationship_id="participates_in_stream",
  pref_label_ja="配信に出演する",
  definition_ja="配信者が配信に出演するイベント (コラボ含む)",
  domain="Streamer",
  range="Stream",
  extension={"namespace": "kimball", "data": {
    "fact": "fct_collaboration",
    "fact_grain": "1 streamer × 1 stream の出演",
    "measures": ["collab_count", "duration_minutes", "peak_concurrent_viewers"],
    "measure_additivity": {"collab_count": "additive",
                           "duration_minutes": "additive",
                           "peak_concurrent_viewers": "semi-additive"},
    "fact_type": "transaction"
  }}
)
→ Saved: ontology/relationships/participates_in_stream.jsonld
```

### 例 2: Conformed Dim 発見 (新規 Dim 追加)

```text
User: 「決済方法というディメンションも追加したい」

Claude: (ディスカバリ) query_concept "決済" → ヒットゼロ → 新規

Claude: (Q1 = concept name) "PaymentMethod" で良い?
User: yes

Claude: (Q2 definition) 1 文で説明
User: 顧客が支払いに使う方法 (クレジットカード/QR コード/...)

Claude: (Q10 SCD type) Type 1 (履歴破棄、上書き) で良さそう?
User: 良い

Claude: → mcp__metamesh__add_concept(
  concept_id="PaymentMethod",
  pref_label_ja="決済方法",
  definition_ja="顧客が支払いに使う方法",
  extension={"namespace": "kimball", "data": {
    "dimension": "dim_payment_method",
    "scd_type": 1
  }}
)
```

## アンチパターン

- ❌ **CBC ディスカバリをスキップ** → 既存 Streamer Concept があるのに
   別名 ("VTuber" 等) で重複登録、Conformed Dim 設計が破綻
- ❌ **Who/What に時間を使い過ぎる** → 既存 Concept を選ぶフェーズに
   過ぎないのに、定義論議を再燃させる。エンティティ議論は CBC、こちらは
   measurement 議論
- ❌ **measure の additivity を聞かない** → 後で BI で "なぜか合計値が
   おかしい" 事故。semi/non-additive は明示的に分類
- ❌ **fact_grain を曖昧にする** → Fact 1 行が何を意味するか不明だと、
   集計クエリが書けなくなる
- ❌ **degenerate dimension と通常 Dim を混同** → 低カーディナリティで
   独立 Dim にする価値がない属性 (例: `participant_role: owner|guest`) は
   Fact 行に直接持つ
- ❌ **既存 dv: 拡張を上書きする呼び方** → ⚠️ 既知の制約を読む。Issue
   #21 が解決するまで手編集 or 待機
- ❌ **`add_concept` を Fact のために呼ぶ** → Fact はイベント=関係性
   なので `add_relationship` 側。`add_concept` は Dim 用
