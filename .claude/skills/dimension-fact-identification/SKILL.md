---
name: dimension-fact-identification
description: ユーザーが Kimball Dimensional Model の Dim/Fact 構造の品質チェック・整合性検証を求めたとき — Conformed Dimension の発見・オーファン Dim 検出・Fact grain 文書化漏れ・SCD Type 未指定などを SPARQL で機械的に検出し、指摘リストを Markdown で返す read-only 診断 Skill。`mcp__metamesh__query_concept` のみ使用、オントロジー編集は行わない。`ontology-review` の Kimball 系対称版。トリガー例: 「Conformed Dim を見つけて」「Dimensional model のレビュー」「Fact 設計の整合性チェック」「Star Schema の健康診断」。
---

# Dimension / Fact 整合性診断 (read-only)

`kimball:` 拡張を持つ Concept (Dimension) と Relationship (Fact) を
SPARQL で網羅的に走査し、Star Schema 設計に発展する前段階で気付くべき
品質問題を検出する Skill。**read-only**、データには手を触れない。

## 拠って立つ業界プラクティス

本 Skill の診断項目は **Kimball Group の "4-Step Dimensional Design Process"**
を下敷きにしている (出典: Ralph Kimball & Margy Ross _The Data Warehouse
Toolkit, 3rd ed._ Wiley, 2013):

1. **Select the business process** (対象業務プロセスの選択) — 対象業務
   プロセスを 1 つ選ぶ
2. **Declare the grain** (粒度の宣言) — Fact 1 行の意味 (粒度) を
   **最初に** 宣言する (= 後付け不能の最重要決定。本 Skill が「Fact
   grain 未文書化」を重要度 Major で検出する根拠)
3. **Identify the dimensions** (Dimension の特定) — 7Ws (Who/What/When/
   Where/Why/How/How many) から Dim 候補を引き出す
4. **Identify the facts** (Fact の特定) — measure を抽出する

加えて、Kimball の **Enterprise Data Warehouse Bus Matrix** (Facts ×
Dimensions の交差表) は Conformed Dim 発見の業界標準成果物。本 Skill の
最重要出力はこの Bus Matrix の機械生成版。

## 診断対象 (6 種)

| # | 項目 | Kimball 用語との対応 |
|---|---|---|
| 1 | **Conformed Dimension** (2 facts 以上から参照) | "Conformed Dimensions" — Bus Matrix の交差点が多い Dim |
| 2 | **Bus Matrix 全体** | Facts × Dims 交差表 (本 Skill の核心出力) |
| 3 | **オーファン Dim / Fact** | 定義したが未参照、または参照軸なし |
| 4 | **未マーク Dim 候補** | Fact が参照しているが `kimball:dimension` 宣言なし |
| 5 | **SCD Type 未指定** | Type 0/1/2/3/4/6/7 (Kimball SCD 種別) のいずれも未指定 |
| 6 | **Fact grain 未文書化** | Step 2 (Declare the grain) のスキップ = 後で集計クエリが破綻 |

## Dimension の種別語彙 (Kimball 標準分類)

将来 `mcp__metamesh__add_concept` 経由で `kimball:dimension_type`
拡張を追加する余地のため、本 Skill は以下の Dim 種別語彙を認識する:

| 種別 | 説明 |
|---|---|
| **Conformed** | 複数 Fact / 複数 Mart で共有 (例: dim_customer, dim_date) |
| **Junk** | 低カーディナリティの Boolean / フラグ群を 1 Dim にまとめる (例: order_status + is_giftwrapped + payment_method の組み合わせ) |
| **Degenerate** | Fact 行に直接持つ低カーディナリティ属性、別テーブル不要 (例: order_number, transaction_id) |
| **Role-Playing** | 同一 Dim を異なる role で参照 (例: dim_date を order_date / ship_date / due_date として使う) |
| **Outrigger** | Dim から Dim を参照 (Snowflake schema のサブ Dim) |
| **Mini-Dimension** | 高頻度更新属性を本 Dim から分離 (SCD Type 2 行爆発を回避) |

現状 (v1) 検出は Conformed のみ機械化、他は **「定義時に種別を明示
すべき」** と Major 警告するに留める。

## Fact の種別語彙 (Kimball 標準分類)

| 種別 | grain の典型 |
|---|---|
| **Transaction Fact** | 1 トランザクション = 1 行 (例: 1 注文行 = fct_order_line) |
| **Periodic Snapshot Fact** | 定期スナップショット (例: 月末残高 = fct_account_balance_monthly) |
| **Accumulating Snapshot Fact** | プロセス進行を 1 行に集約 (例: 注文 → 配送 → 完了 = fct_order_pipeline) |
| **Factless Fact** | measure 列が無い、参加事実だけ記録 (例: 出席記録) |
| **Aggregated Fact** | 上位粒度に集約済み (例: 日別集計テーブル) |

「Declare the grain」原則の実装上の意味は: **Transaction Fact なら何の
1 行か、Snapshot なら何時点の何か、Accumulating なら何のプロセスの何
ステップ完了か** を `kimball:fact_grain` 文字列で明示しろ、ということ。

## 前提条件

- `mcp__metamesh__query_concept` が利用可能 (SPARQL SELECT モード)
- 副作用ゼロ。`mcp__metamesh__add_concept` /
  `mcp__metamesh__add_relationship` は一切呼ばない
- BEAM インタビュー (`beam-modeling-interview` Skill) で `kimball:`
  拡張が既に登録されていること (オーファン状態だけでも診断可能、
  ただし全体が空なら結果も空)

## 診断チェックの SPARQL レシピ

### 1. Conformed Dimension の発見 (Star Schema 設計の核心)

複数 Fact から参照される Dimension を抽出。BI 横断分析や ETL 統合の
基盤になる候補:

```sparql
PREFIX kimball: <https://metamesh.dev/ext/kimball/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT
    ?dim
    (COUNT(DISTINCT ?fact_rel) AS ?fact_count)
    (GROUP_CONCAT(DISTINCT ?fact_name; SEPARATOR=", ") AS ?used_by)
WHERE {
    ?dim kimball:dimension ?dim_name .
    ?fact_rel kimball:fact ?fact_name .
    {
        ?fact_rel rdfs:domain ?dim .
    } UNION {
        ?fact_rel rdfs:range ?dim .
    }
}
GROUP BY ?dim
HAVING (COUNT(DISTINCT ?fact_rel) >= 2)
ORDER BY DESC(?fact_count)
```

→ `fact_count >= 2` のものは **Conformed Dim 確定**。Mart 設計時に
共有テーブルとして 1 つだけ作る。

### 2. オーファン Dimension (定義したが使ってない)

```sparql
PREFIX kimball: <https://metamesh.dev/ext/kimball/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?dim ?label WHERE {
    ?dim kimball:dimension ?_dim_name ;
         skos:prefLabel ?label .
    FILTER(LANG(?label) = "ja")
    FILTER NOT EXISTS {
        ?_fact_rel kimball:fact ?_ ;
                   rdfs:domain|rdfs:range ?dim .
    }
}
ORDER BY ?dim
```

→ 「使う予定だが Fact 未定義」or 「もう要らない」のどちらか。判断は
ユーザーに委ねる。

### 3. オーファン Fact (集計軸 = Dim を持たない)

```sparql
PREFIX kimball: <https://metamesh.dev/ext/kimball/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?fact_rel ?fact_name WHERE {
    ?fact_rel kimball:fact ?fact_name .
    FILTER NOT EXISTS {
        ?fact_rel rdfs:domain ?d .
        ?d kimball:dimension ?_ .
    }
    FILTER NOT EXISTS {
        ?fact_rel rdfs:range ?r .
        ?r kimball:dimension ?_ .
    }
}
```

→ Fact が Dim を持たない = 「いつ・誰の・何の」を集計できない
変な Fact。**Critical** で報告。

### 4. 未マーク Dim 候補 (Fact が参照してるが kimball:dimension が無い Concept)

```sparql
PREFIX kimball: <https://metamesh.dev/ext/kimball/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT ?missing ?label WHERE {
    ?_fact_rel kimball:fact ?_fact_name .
    {
        ?_fact_rel rdfs:domain ?missing .
    } UNION {
        ?_fact_rel rdfs:range ?missing .
    }
    ?missing a skos:Concept .
    OPTIONAL { ?missing skos:prefLabel ?label . FILTER(LANG(?label) = "ja") }
    FILTER NOT EXISTS { ?missing kimball:dimension ?_ }
}
ORDER BY ?missing
```

→ Fact は使ってるが `kimball:dimension` 宣言が無い Concept。**Major**
で「Dim としてマークすべき」と提示。`mcp__metamesh__add_concept`
(extension list 形式) で kimball: を追加する手順を添える。

### 5. SCD Type 未指定 Dim

```sparql
PREFIX kimball: <https://metamesh.dev/ext/kimball/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?dim ?label WHERE {
    ?dim kimball:dimension ?_dim_name .
    OPTIONAL { ?dim skos:prefLabel ?label . FILTER(LANG(?label) = "ja") }
    FILTER NOT EXISTS { ?dim kimball:scd_type ?_ }
}
ORDER BY ?dim
```

→ 履歴管理戦略未決定 = Type 1 (上書き) で済むのか、Type 2 (履歴保存)
が要るのか確認すべし。**Warning** で報告。

### 6. Fact grain 未文書化

```sparql
PREFIX kimball: <https://metamesh.dev/ext/kimball/>

SELECT ?fact_rel ?fact_name WHERE {
    ?fact_rel kimball:fact ?fact_name .
    FILTER NOT EXISTS { ?fact_rel kimball:fact_grain ?_ }
}
ORDER BY ?fact_rel
```

→ Fact 1 行が何を意味するか不明 = 集計の意味が定まらない。
**Major** で報告、`beam-modeling-interview` の grain 質問に戻るよう案内。

## 出力フォーマット (1): Bus Matrix (Kimball 標準形式)

Kimball Group の "Enterprise DW Bus Matrix" を機械生成する。Facts ×
Dims の交差表で、`✓` が「この Fact がこの Dim を参照する」、空欄が
「参照なし」。Conformed Dim は **複数列に ✓ が並ぶ Dim** として視覚的に
特定できる。

```markdown
## Bus Matrix

|                          | dim_streamer | dim_stream | dim_channel | dim_topic | dim_date |
|--------------------------|:---:|:---:|:---:|:---:|:---:|
| fct_collaboration        | ✓ | ✓ |    |    | ✓ |
| fct_view_count           | ✓ | ✓ |    |    | ✓ |
| fct_subscription_change  | ✓ |    | ✓ |    | ✓ |

**Conformed Dimensions** (2 つ以上の Fact から参照): `dim_streamer` (3 facts), `dim_stream` (2 facts), `dim_date` (3 facts)
```

生成 SPARQL は §1 の Conformed Dim クエリを応用 (Dim ごとに参照 Fact
を集約してマトリックス化)。

## 出力フォーマット (2): 重要度別の検出結果

各チェックの結果を重要度 (Critical / Major / Warning / Info) 別に
Markdown でまとめる:

```markdown
# Dimensional Model 整合性レビュー結果

検査対象: 2 facts, 6 dimensions

## ✅ Critical (要即修正)
✅ 該当なし

## 🟠 Major (修正推奨)
- **[未マーク Dim]** `Channel` (チャンネル) — `fct_collaboration` から
  range 参照されているが `kimball:dimension` 宣言が無い。
  → `mcp__metamesh__add_concept` の extension に
    `[..., {"namespace": "kimball", "data": {"dimension": "dim_channel", "scd_type": 2}}]`
    を追加して再登録
- **[Fact grain 未文書化]** `participates_in_stream` — `kimball:fact_grain`
  が空。**1 streamer × 1 stream の出演** など明示すべし
  → `mcp__metamesh__add_relationship` の extension data に
    `"fact_grain": "..."` を追加

## 🟡 Warning (検討)
- **[SCD Type 未指定]** `Streamer` (配信者) — Type 1/2/3 のいずれか決める
- **[オーファン Dim]** `Topic` (トピック) — 現在どの Fact からも参照なし。
  使う予定があるなら Fact を追加、無いなら `kimball:dimension` 宣言を
  外す検討を

## ℹ️ Info (参考)
- **[Conformed Dim]** `Streamer` is used by **2 facts**:
  fct_collaboration, fct_subscription_change
  → Mart 設計時に dim_streamer は共有テーブル化
- **[Conformed Dim]** `Stream` is used by **2 facts**:
  fct_collaboration, fct_view_count
```

## 重要度判断基準

| 重要度 | 例 | 対処指針 |
|---|---|---|
| ✅ Critical | オーファン Fact (Dim を持たない) | 即修正、Star Schema 設計不能 |
| 🟠 Major | 未マーク Dim 候補、Fact grain 未文書化 | 早急に対応、無いと物理設計が機械化できない |
| 🟡 Warning | SCD Type 未指定、オーファン Dim | 設計判断が要る、放置で OK な場合もある |
| ℹ️ Info | Conformed Dim 発見 | 物理設計時に共有テーブル化を考慮 |

**Conformed Dim の検出は "問題" ではなく "発見"**。Info レベルで
ポジティブに報告するのが本 Skill の特徴。

## 例

### 例 1: 全体ヘルスチェック

```text
User: 「Dimensional model をレビューして」

Claude:
  → 6 つのチェック SPARQL を順に実行 (mcp__metamesh__query_concept)
  → 結果を重要度別に集計
  → 上記フォーマットで Markdown 返答
```

### 例 2: Conformed Dim だけ知りたい

```text
User: 「Conformed Dim を見つけて」

Claude:
  → §1 の SPARQL のみ実行
  → 該当が空なら "✅ Conformed Dim はまだ発見されず (Fact が 1 つしか
     ないか、Dim 共有が無い)" と返す
  → あれば list で返し、各 Dim の参照 Fact 一覧を添える
```

### 例 3: BEAM 直後のチェック

```text
User: 「今 BEAM で配信イベントを 3 つ登録した。問題ある?」

Claude:
  → Major チェック (未マーク Dim、Fact grain 未文書化) を優先実行
  → 該当があれば即対応案を提示、無ければ Conformed Dim 候補を見せる
```

## 可視化との連携

`ontology-visualize` Skill と組み合わせると、Dim-Fact グラフが見える:

> 「全 Fact と Dim を Mermaid で見せて」 → ontology-visualize Skill 起動
> (内部で `?fact rdfs:domain|rdfs:range ?dim` の CONSTRUCT)

Conformed Dim はグラフ上で **複数の Fact から伸びるノード** として
視覚的に分かる。

## アンチパターン

- ❌ **このスキルからオントロジーを書き換えない** — read-only。修正は
  `beam-modeling-interview` で人間が判断して
  `mcp__metamesh__add_concept` / `mcp__metamesh__add_relationship` を呼ぶ
- ❌ **Conformed Dim を "問題" として報告する** — むしろ発見・歓迎
  すべきもの。Info で前向きに表示
- ❌ **未マーク Dim を勝手に kimball:dimension 追加する** — 「Dim と
  すべき」は提案までで、実行はユーザー承認 + `beam-modeling-interview`
  経由
- ❌ **SCD Type を機械的に Type 2 サジェスト** — Type の選択は履歴
  要件次第。決定はユーザーに委ねる
- ❌ **6 つすべてを毎回フル実行する** — ユーザーが特定種類だけ知りたい
  なら該当 SPARQL のみ実行
- ❌ **`kimball:` 拡張が空の repo で空結果を出して終わる** — まず
  「`kimball:` 拡張が登録された Concept/Relationship が存在しません。
  `beam-modeling-interview` から始めましょう」と案内
- ❌ **DV 拡張 (`dv:hub` 等) を診断対象に含める** — このスキルは
  Kimball 専用。DV 側の診断は `ontology-review` に委ねる

## 参考文献 (本 Skill 設計の典拠)

- **Ralph Kimball & Margy Ross** _The Data Warehouse Toolkit, 3rd ed._
  (Wiley, 2013) — 4-Step Dimensional Design Process / Bus Matrix /
  Conformed Dim / SCD Type 0-7
- **Lawrence Corr & Jim Stagnitto** _Agile Data Warehouse Design_
  (DecisionOne Press, 2011) — BEAM 7Ws、本 Skill の入力側 (BEAM Skill
  経由) を整理
- **Kimball Group "Dimensional Modeling Techniques"** —
  https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/
  (Dim 種別: Conformed / Junk / Degenerate / Role-Playing / Outrigger /
  Mini-Dim の公式分類典拠)
- **Kimball Group "Slowly Changing Dimension Techniques"** —
  https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/slowly-changing-dimension/
  (SCD Type 0/1/2/3/4/6/7 の公式定義)
