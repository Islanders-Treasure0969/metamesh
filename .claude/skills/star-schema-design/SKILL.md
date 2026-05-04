---
name: star-schema-design
description: ユーザーが Kimball Dimensional Model の物理設計 (Star/Snowflake Schema) を生成したい・Fact/Dim テーブル DDL を作りたい・dbt model の雛形が欲しいとき、`mcp__metamesh__query_concept` でオントロジーから `kimball:` 拡張付きの Concept (Dim) と Relationship (Fact) を抽出し、対応する Star Schema 物理設計を Markdown / Snowflake DDL / BigQuery DDL / PostgreSQL DDL / dbt model / dbt snapshot / dbt schema.yml のいずれかで生成する Skill。`dv-implementation-design` の Kimball 系対称版。トリガー例: 「Star Schema を生成して」「dim_customer の DDL を出して」「dbt 雛形で fact テーブル作って」「Snowflake で Dimensional Model を物理化」。
---

# Star Schema 物理設計

オントロジー上の Kimball 拡張メタデータ (`kimball:dimension` /
`kimball:fact` / `kimball:scd_type` / `kimball:fact_grain` /
`kimball:measures` 等) を、**Star Schema の物理設計** (Fact + Dim テーブル
群) に翻訳する Skill。

`mcp__metamesh__query_concept` を SPARQL で叩いて取得 → 設計ドキュメントを
クライアント側で組み立てる、というパターン。`dv-implementation-design` と
同じ構造。

## 拠って立つ業界プラクティス

本 Skill は **3 つの設計学派** を認識した上で出力を切り替える:

| 学派 | 中核 | 出典 |
|---|---|---|
| **Classic Kimball** (default) | 厳格 Star Schema、Conformed Dim 共有、`dim_/fct_` プレフィックス | Ralph Kimball & Margy Ross _The Data Warehouse Toolkit, 3rd ed._ (Wiley, 2013) / Christopher Adamson _Star Schema The Complete Reference_ (2010) |
| **Modern dbt "Wide & Denormalized"** | Dim を Fact に joined-and-flattened、命名は業務名 | dbt Labs 公式 [How we structure our dbt projects](https://docs.getdbt.com/best-practices/how-we-structure/4-marts) |
| **Hybrid (DV Raw + Star Mart)** | Raw 層は Hub/Link/Sat、Mart 層は Star | 業界実態の多数派 (Linstedt + Kimball 合流) |

**default は Classic** (業界実態として `dim_/fct_` プレフィックス + 厳格
Star が依然多数派)。Modern dbt 派の主張も理に適っているが、選択肢として
`mode="wide"` 引数で切替可能にする。

## 前提条件

- `mcp__metamesh__query_concept` が利用可能
- オントロジーに `kimball:` 拡張付きの Concept / Relationship が登録済み
  (無ければまず `beam-modeling-interview` Skill を案内)
- 設計開始前に `dimension-fact-identification` Skill を実行して **Bus
  Matrix の整合性** (Conformed Dim / オーファン Dim / Fact grain 文書化)
  を確認しておくことを強く推奨

## Skill 引数

```python
mcp__metamesh__star_schema_design(
    output_path: str,
    mode: "classic" | "wide" = "classic",
    naming: "kimball_prefix" | "plain" = "kimball_prefix",
    sk_strategy: "hash" | "identity" | "uuid" = "hash",
    dialect: "markdown" | "snowflake" | "bigquery" | "postgres"
             | "dbt_model" | "dbt_snapshot" | "dbt_yaml" = "markdown",
    include_audit_cols: bool = True,
    include_tests: bool = True,
)
```

各引数の意味と選択肢の業界根拠:

### `mode`

| 値 | 内容 | いつ選ぶ |
|---|---|---|
| **`classic`** (default) | 中央 Fact + 周辺 Dim を別テーブル、JOIN 前提 | 伝統的 BI ツール (Tableau / Looker) 接続、Kimball 教科書準拠、Mart 共有 |
| `wide` | Dim を Fact に joined-and-flattened したワイドテーブル | dbt + Snowflake/BigQuery 主体、columnar 圧縮で storage コスト低、JOIN 削減で query 高速化 |

### `naming`

| 値 | 例 | 採用根拠 |
|---|---|---|
| **`kimball_prefix`** (default) | `dim_customer`, `fct_orders`, `agg_sales_monthly` | 業界デファクト、Kimball Toolkit / Adamson 標準、企業 BI ガイドライン主流 |
| `plain` | `customers`, `orders` | dbt Labs 公式 ("use plain English to name the file based on the concept") |

### `sk_strategy`

| 値 | 実装 | 強み | 弱み |
|---|---|---|---|
| **`hash`** (default) | `dbt_utils.generate_surrogate_key([...])` (MD5) | 全 dialect 動作、確定的、distributed 環境対応 | hex 32 文字 |
| `identity` | Snowflake `IDENTITY(1,1)` / Postgres `BIGSERIAL` | 短い key、可読性 | dialect 依存、BigQuery 不可 |
| `uuid` | Snowflake `UUID_STRING()` / BigQuery `GENERATE_UUID()` | 完全一意 | 36 文字、ソート困難 |

### `dialect`

| 値 | 用途 |
|---|---|
| **`markdown`** (default) | レビュー / ドキュメント、最初に出すべき形式 |
| `snowflake` | Snowflake 直適用 (`IDENTITY` / `TIMESTAMP_NTZ` / `BINARY`) |
| `bigquery` | BigQuery 直適用 (`STRING` / `TIMESTAMP` / `CLUSTER BY`) |
| `postgres` | OSS dialect (`SERIAL` / `gen_random_uuid()`) |
| `dbt_model` | dbt model `.sql` 雛形 (incremental / table) |
| `dbt_snapshot` | dbt snapshot `.sql` 雛形 (SCD Type 2 専用) |
| `dbt_yaml` | dbt schema.yml (test + documentation) |

## SCD Type 0〜7 のサポートと dbt 対応

物理化の核心。`kimball:scd_type` から以下にマップする:

| SCD Type | 名称 | 物理実装 | dbt 実装 |
|---|---|---|---|
| **Type 0** | Retain Original | カラム追加なし、不変 | dbt model + immutable test |
| **Type 1** | Overwrite | UPDATE、履歴破棄 | dbt model `materialized: 'table'` または incremental (insert/overwrite) |
| **Type 2** | Add New Row | surrogate key + valid_from + valid_to + is_current | **`dbt snapshot`** (公式 native) ← 最頻出 |
| Type 3 | Add New Attribute | original_X + current_X 列並列 | dbt model + 列追加 |
| Type 4 | Add History Table | dim_current + dim_history 分離 | dbt model 2 つ |
| Type 5 | Mini-Dimension | base + mini + bridge | dbt model 3 つ |
| Type 6 | 1+2+3 Combined | current_X + historical_X + valid_from + valid_to | snapshot + dbt model 組合せ |
| Type 7 | Hybrid (Surrogate + Natural) | Fact に両 key を持つ | dbt model で natural_key 同時保持 |

### dbt snapshot (Type 2 推奨実装)

dbt 公式 snapshot を選んだ場合、metadata カラムは **dbt 流命名** に従う:

| カラム | 意味 |
|---|---|
| `dbt_valid_from` | snapshot 行が valid 化した時刻 |
| `dbt_valid_to` | invalid 化時刻 (NULL = current) |
| `dbt_updated_at` | source の `updated_at` 値 |
| `dbt_scd_id` | snapshot 行ごとの一意 ID |

dbt 1.9+ では `dbt_valid_to_current: '9999-12-31'` で sentinel 値設定可。
本 Skill は default で sentinel 値を採用 (NULL より range query が単純)。

### 手書き Type 2 (snapshot 不採用時)

業界典型の命名:

```sql
valid_from   TIMESTAMP NOT NULL
valid_to     TIMESTAMP NOT NULL DEFAULT TIMESTAMP '9999-12-31'
is_current   BOOLEAN   NOT NULL
```

## 物理設計の規約

### Dim テーブル (Classic mode)

| カラム | 型 | 説明 |
|---|---|---|
| `<dim>_key` | CHAR(32) (hash) / BIGINT (identity) / VARCHAR(36) (uuid) | surrogate key |
| `<business_key>` | (dialect 依存) | natural / business key |
| `<attribute>...` | 各属性列 | descriptive |
| audit columns | TIMESTAMP / VARCHAR | `load_dts`, `update_dts`, `source_system`, `batch_id` |
| (Type 2 のみ) `valid_from` / `valid_to` / `is_current` | TIMESTAMP / BOOLEAN | 履歴管理 |

テーブル名:
- `kimball_prefix`: `dim_<dim_name>` (例: `dim_streamer`)
- `plain`: `<concept_id_snake>` (例: `streamers`)

### Fact テーブル (Classic mode)

| カラム | 型 | 説明 |
|---|---|---|
| `<fact>_key` | (sk_strategy 依存) | Fact 自身の surrogate key |
| `<dim>_key`... | (Dim と同型) | 各 Dim への FK |
| `<measure>...` | NUMERIC / DECIMAL / INT | 集計対象列 |
| `<degenerate_dim>...` | VARCHAR | Fact 行に直接持つ低カーディナリティ属性 (例: `participant_role`) |
| audit columns | 同上 | |

テーブル名:
- `kimball_prefix`: `fct_<fact_name>` (例: `fct_collaboration`)
- `plain`: `<concept_id_snake>` (例: `collaborations`)

### Wide mode (Dim を Fact に joined)

`mode="wide"` のときは **Fact = Dim 全 attribute joined テーブル** を出力:

```sql
-- 例: collaborations (wide mode)
streamer_business_key
streamer_name
streamer_org
stream_business_key
stream_title
stream_topic
participant_role
collab_count
duration_minutes
load_dts
```

→ JOIN コスト削減、Snowflake/BigQuery の columnar 圧縮で storage コスト
低。**Conformed Dim 共有の概念は Wide では消える** (各 Fact に複製される)。

## 設計フロー

1. **Bus Matrix 整合性確認**

   `dimension-fact-identification` Skill を先に実行して、Conformed Dim
   と Fact grain が文書化済みであることを確認。未文書化なら本 Skill は
   実行を中断する。

2. **発見**

   SPARQL で `kimball:dimension` と `kimball:fact` の Concept /
   Relationship を取得:

   ```sparql
   PREFIX kimball: <https://metamesh.dev/ext/kimball/>
   PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
   PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

   SELECT ?dim ?dim_name ?label ?scd_type WHERE {
       ?dim kimball:dimension ?dim_name .
       OPTIONAL { ?dim kimball:scd_type ?scd_type }
       OPTIONAL { ?dim skos:prefLabel ?label . FILTER(LANG(?label) = "ja") }
   }
   ```

   ```sparql
   PREFIX kimball: <https://metamesh.dev/ext/kimball/>
   PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

   SELECT ?fact ?fact_name ?grain ?domain ?range WHERE {
       ?fact kimball:fact ?fact_name ;
             rdfs:domain ?domain ;
             rdfs:range ?range .
       OPTIONAL { ?fact kimball:fact_grain ?grain }
   }
   ```

3. **引数確認**

   ユーザーに `mode` / `naming` / `sk_strategy` / `dialect` を確認。
   未指定なら default を使う。

4. **生成**

   各 Dim / Fact に対して規約に従って出力。Conformed Dim は (Classic mode
   なら) 1 度だけ生成し、複数 Fact から FK で参照させる。

5. **schema.yml 同時生成** (`include_tests=True` 時)

   ```yaml
   models:
     - name: dim_streamer
       columns:
         - name: dim_streamer_key
           tests:
             - unique
             - not_null
     - name: fct_collaboration
       columns:
         - name: dim_streamer_key
           tests:
             - not_null
             - relationships:
                 to: ref('dim_streamer')
                 field: dim_streamer_key
   ```

6. **次の一手**

   生成完了後、ユーザーに以下を提案:
   - 別 dialect での生成 (例: Markdown 後に dbt_model)
   - dbt project への組み込み手順
   - SCD Type を変更する場合の再生成

## 出力テンプレート

### Markdown (default)

```markdown
# Star Schema 物理設計 — VTuber 分析ドメイン (Classic mode)

## Dim テーブル

### `dim_streamer` (SCD Type 2)

| カラム | 型 | 説明 |
|---|---|---|
| `dim_streamer_key` | CHAR(32) | `dbt_utils.generate_surrogate_key(['lower(trim(streamer_id))'])` |
| `streamer_id` | VARCHAR | business key |
| `streamer_name` | VARCHAR | |
| `valid_from` | TIMESTAMP | |
| `valid_to` | TIMESTAMP | |
| `is_current` | BOOLEAN | |
| `load_dts` | TIMESTAMP | |
| `source_system` | VARCHAR | |

(他の Dim も同様)

## Fact テーブル

### `fct_collaboration` (Transaction Fact)

**Grain**: 1 streamer × 1 stream の出演 1 件

| カラム | 型 | 説明 |
|---|---|---|
| `fct_collaboration_key` | CHAR(32) | surrogate key |
| `dim_streamer_key` | CHAR(32) | FK → `dim_streamer` |
| `dim_stream_key` | CHAR(32) | FK → `dim_stream` |
| `participant_role` | VARCHAR | degenerate dim (owner / guest) |
| `collab_count` | INT | additive measure |
| `duration_minutes` | DECIMAL(10,2) | additive measure |
| `peak_concurrent_viewers` | INT | semi-additive measure (平均にしか意味なし) |
| `load_dts` | TIMESTAMP | |
```

### Snowflake DDL

```sql
CREATE OR REPLACE TABLE dim_streamer (
    dim_streamer_key   BINARY(16)         NOT NULL,
    streamer_id        VARCHAR             NOT NULL,
    streamer_name      VARCHAR,
    valid_from         TIMESTAMP_NTZ       NOT NULL,
    valid_to           TIMESTAMP_NTZ       NOT NULL DEFAULT '9999-12-31',
    is_current         BOOLEAN             NOT NULL,
    load_dts           TIMESTAMP_NTZ       NOT NULL,
    source_system      VARCHAR             NOT NULL,
    CONSTRAINT pk_dim_streamer PRIMARY KEY (dim_streamer_key)
);
```

### dbt snapshot (SCD Type 2)

```sql
-- snapshots/dim_streamer_snapshot.sql
{% snapshot dim_streamer_snapshot %}

{{
    config(
        target_schema='snapshots',
        unique_key='streamer_id',
        strategy='timestamp',
        updated_at='source_updated_at',
        dbt_valid_to_current="'9999-12-31'"
    )
}}

SELECT
    streamer_id,
    streamer_name,
    org,
    source_updated_at
FROM {{ source('staging', 'streamers') }}

{% endsnapshot %}
```

### dbt model (Type 1, Markdown レビュー後)

```sql
-- models/marts/dim_topic.sql
{{
    config(
        materialized='table'
    )
}}

WITH source AS (
    SELECT * FROM {{ source('staging', 'topics') }}
),

renamed AS (
    SELECT
        {{ dbt_utils.generate_surrogate_key(['lower(trim(topic_id))']) }} AS dim_topic_key,
        topic_id,
        topic_name,
        topic_category,
        CURRENT_TIMESTAMP()                                              AS load_dts,
        'holodex_api'                                                    AS source_system
    FROM source
)

SELECT * FROM renamed
```

### dbt schema.yml (test + doc 同時生成)

```yaml
version: 2

models:
  - name: dim_streamer
    description: Streamer dimension (SCD Type 2 via snapshot)
    columns:
      - name: dim_streamer_key
        tests:
          - unique
          - not_null
      - name: streamer_id
        tests:
          - not_null

  - name: fct_collaboration
    description: Transaction Fact for streamer collaboration events
    columns:
      - name: fct_collaboration_key
        tests:
          - unique
          - not_null
      - name: dim_streamer_key
        tests:
          - not_null
          - relationships:
              to: ref('dim_streamer')
              field: dim_streamer_key
      - name: dim_stream_key
        tests:
          - not_null
          - relationships:
              to: ref('dim_stream')
              field: dim_stream_key
```

## アンチパターン

業界プラクティスに反するパターンは Skill 内で明示禁止:

- ❌ **Fact の grain を曖昧にする** — Kimball 4-Step Step 2 違反、後で
  集計クエリが破綻
- ❌ **Conformed Dim を Mart 別に複製生成** (Classic mode で) — 業務全体
  の一貫性が崩れる。Wide mode は逆に意図的に複製する哲学なので OK
- ❌ **surrogate key 入力の前処理を省略** (`lower(trim())` を通さない) —
  揺れで別 hash になり、整合性破綻
- ❌ **audit columns 省略** (`load_dts` / `source_system` 等) — 障害時
  の追跡不能
- ❌ **schema.yml の `unique` / `not_null` テスト省略** — 重複データ /
  欠損 PK の発見が遅れる
- ❌ **Bridge / Mini-Dim / Outrigger / Late-arriving / Junk Dim を勝手に
  生成** — 高度パターンは要明示要求、自動生成は危険
- ❌ **Snowflake で `IDENTITY` を分散環境で使う** — 順序保証コストが
  scale で問題化、`hash` 推奨
- ❌ **BigQuery で `IDENTITY` を試みる** — ネイティブサポート無し
- ❌ **どの mode (classic / wide) か聞かずに決める** — 設計哲学が違う、
  ユーザー確認必須
- ❌ **どの dialect か聞かずに決める** — Snowflake / BigQuery / Postgres
  は型・関数が大きく違う
- ❌ **SCD Type を機械的に Type 2 サジェスト** — 履歴要件次第。Type 1 で
  十分なケースもある (`Topic` 等の static reference)

## 高度パターン (本 Skill v1 では出力しない)

将来の拡張候補だが、現状は明示要求があっても **「v1 ではサポート外」と
明記して別 Skill / 手書き案内** に留める:

| パターン | 概要 | スコープ外の理由 |
|---|---|---|
| **Bridge Tables** | M:N 関係解決テーブル | 設計判断要、`kimball:bridge` 拡張未実装 |
| **Mini-Dimension** | 高頻度更新属性を別 Dim に分離 | `kimball:dimension_type: mini` 拡張未実装 |
| **Outrigger Dimension** | Dim から別 Dim を参照 (Snowflake schema 化) | 設計判断要 |
| **Late-Arriving Facts/Dims** | 後から到着するイベント対応 | ETL 戦略の領域 |
| **Junk Dimension** | 低カーディナリティ Boolean を 1 Dim にまとめる | アンチパターン気味、要明示要求 |

## 参考文献 (本 Skill 設計の典拠)

- **Ralph Kimball & Margy Ross** _The Data Warehouse Toolkit, 3rd ed._
  (Wiley, 2013) — 4-Step Dimensional Design Process / Bus Matrix /
  Conformed Dim / SCD Type 体系
- **Christopher Adamson** _Star Schema The Complete Reference_
  (McGraw-Hill, 2010) — `dim_/fct_` 命名規約、Bridge / Mini-Dim
  パターン
- **Lawrence Corr & Jim Stagnitto** _Agile Data Warehouse Design_
  (DecisionOne Press, 2011) — BEAM 7Ws (本 Skill の上流)
- **Daniel Linstedt & Michael Olschimke** _Building a Scalable Data
  Warehouse with Data Vault 2.0_ (Morgan Kaufmann, 2015) — Hybrid 戦略
  (Raw Vault → Star Mart) の典拠
- **Wikipedia "Slowly Changing Dimension"** — SCD Type 0-7 完全分類
- **dbt Labs 公式: How we structure our dbt projects** —
  https://docs.getdbt.com/best-practices/how-we-structure/4-marts
  (Wide & Denormalized 哲学、`plain` 命名規約)
- **dbt Labs 公式: Snapshots** —
  https://docs.getdbt.com/docs/build/snapshots
  (SCD Type 2 native 実装、metadata カラム命名)
- **dbt-utils** —
  https://github.com/dbt-labs/dbt-utils
  (`generate_surrogate_key` macro)
- **Kimball Group "Dimensional Modeling Techniques"** /
  **"Slowly Changing Dimension Techniques"** —
  https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/
  (Dim 種別 / SCD Type の公式分類)
