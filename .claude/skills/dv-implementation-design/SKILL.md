---
name: dv-implementation-design
description: ユーザーがオントロジーから Data Vault の物理設計 (Hub / Link テーブル) を作りたい・DDL を生成したい・dbt モデルの雛形が欲しいとき、`mcp__metamesh__query_concept` で DV 拡張 (`dv:hub` / `dv:link`) 付きの concept・relationship を抽出し、対応する Hub/Link テーブル定義を Markdown / DDL (Snowflake / BigQuery / 汎用) / dbt モデル雛形のいずれかで生成する Skill。トリガー例: 「DV の物理設計を出して」「Hub テーブル一覧を DDL で」「dbt モデル雛形を作って」「LNK_COLLAB の物理スキーマは？」。
---

# DV (Data Vault) 物理設計

オントロジー上の DV 拡張メタデータ (`dv:hub` / `dv:link` / `dv:business_key` /
`dv:cardinality` / `dv:role_attribute` 等) を読み取って、**Hub / Link テーブル
の物理設計** に翻訳する Skill。

`mcp__metamesh__query_concept` を SPARQL で叩いて取得 → 設計ドキュメントを
クライアント側で組み立てる、というパターン。組み込みの generator (Skill の
外側にあるツール) は使わない。

## 前提条件

- `mcp__metamesh__query_concept` が利用可能
- オントロジーに `dv:` 拡張が付いた concept / relationship が存在する
  (無いとそもそも生成対象が無い → `cbc-modeling-interview` で先に Hub
  指定を追加するよう案内)
- 出力形式 (Markdown / Snowflake DDL / BigQuery DDL / 汎用 DDL / dbt model)
  の選択肢をユーザーに提示する

## 出力形式の選択ガイド

| 形式 | 用途 | 強み |
|---|---|---|
| **Markdown 表** (既定) | レビュー / ドキュメント | チャット内で可読、レビューしやすい |
| **Snowflake DDL** | Snowflake への直接適用 | `MD5()`, `TIMESTAMP_NTZ`, `VARIANT` 等を活用 |
| **BigQuery DDL** | BigQuery への直接適用 | `TO_HEX(MD5(x))`, `TIMESTAMP` 型 |
| **汎用 SQL DDL** | 移植性重視 | `VARCHAR(N)`, ANSI SQL に近い |
| **dbt モデル雛形** | dbt プロジェクトへの組み込み | `dbt_utils.generate_surrogate_key`, ref/source 関数 |

ユーザーが指定しなければ Markdown を既定として出し、続けて他形式が
必要か聞く。

## 物理設計の規約

### Hub テーブル

| カラム | 型 | 説明 |
|---|---|---|
| `<hub_name>_hk` | CHAR(32) / BINARY(16) | Hash key (md5(lower(trim(business_key)))) |
| `<business_key_column>` | VARCHAR | ビジネスキー本体 (例: `channel_id`) |
| `load_dts` | TIMESTAMP | レコード初回ロード時刻 |
| `rec_src` | VARCHAR | データソース識別子 (例: `holodex_api`) |

テーブル名: `hub_<hub_name_lowercase>` (例: `hub_streamer`)

### Link テーブル

| カラム | 型 | 説明 |
|---|---|---|
| `<link_name>_hk` | CHAR(32) / BINARY(16) | Link 自身の hash key (md5(concat domain_hk + range_hk + ...)) |
| `<domain_concept>_hk` | CHAR(32) | domain 側 Hub の hash key (FK) |
| `<range_concept>_hk` | CHAR(32) | range 側 Hub の hash key (FK) |
| `load_dts` | TIMESTAMP | |
| `rec_src` | VARCHAR | |
| `<role_attribute>` | VARCHAR | (`dv:role_attribute` で指定された場合のみ。例: `participant_role`) |

テーブル名: `lnk_<link_name_lowercase>` (例: `lnk_streamer_channel`)

### Hash key 生成ポリシー

- アルゴリズム: **MD5** (既定) / SHA1 (代替、衝突耐性ニーズで切替)
- 入力前処理: `lower(trim(<business_key>))` で揺れを吸収
- Link hash key: 関連する Hub hash key をチルダ区切り (`~`) で連結 →
  さらに MD5。**区切り子は環境を跨いで `~` 一択に固定すること** (既定が
  揺れると同じビジネスキーから別 hash が生まれて整合性が壊れる)

```sql
-- Hub
md5(lower(trim(channel_id))) AS channel_hk

-- Link (Streamer × Channel)
md5(
    streamer_hk || '~' ||
    channel_hk
) AS streamer_channel_hk
```

## 設計フロー

1. **発見**: SPARQL SELECT で Hub / Link 一覧を取得:
   ```sparql
   PREFIX dv: <https://metamesh.dev/ext/dv/>
   PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

   SELECT ?concept ?label ?hub ?bk WHERE {
       ?concept dv:hub ?hub ;
                skos:prefLabel ?label .
       OPTIONAL { ?concept dv:business_key ?bk }
       FILTER(LANG(?label) = "ja")
   }
   ORDER BY ?hub
   ```
   ```sparql
   PREFIX dv: <https://metamesh.dev/ext/dv/>
   PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
   PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

   SELECT ?rel ?label ?link ?domain ?range ?card ?role WHERE {
       ?rel dv:link ?link ;
            rdfs:domain ?domain ;
            rdfs:range ?range ;
            skos:prefLabel ?label .
       OPTIONAL { ?rel dv:cardinality ?card }
       OPTIONAL { ?rel dv:role_attribute ?role }
       FILTER(LANG(?label) = "ja")
   }
   ORDER BY ?link
   ```

2. **形式選択**: ユーザーに「どの形式で出す？(Markdown / Snowflake DDL / 
   BigQuery DDL / 汎用 / dbt)」と聞く。指定なしなら Markdown。

3. **生成**: 各 Hub / Link に対して上記規約に従って出力。

4. **表示**: 生成結果をチャットに直貼り。複数形式が必要なら追加で生成。

5. **次の一手**: 「dbt project に組み込む方針もガイドする？」「テストの
   設計 (uniqueness / not_null) も加える？」等、続きの作業を提案。

## 出力テンプレート

### Markdown 表 (既定)

````markdown
# DV 物理設計 — VTuber ドメイン

## Hub テーブル

### `hub_streamer`

| カラム | 型 | 説明 |
|---|---|---|
| `streamer_hk` | CHAR(32) | `md5(lower(trim(streamer_id)))` |
| `streamer_id` | VARCHAR | Holodex channel.id (= YouTube UCxxxx) を流用 |
| `load_dts` | TIMESTAMP | |
| `rec_src` | VARCHAR | `holodex_api` |

(他の Hub も同様)

## Link テーブル

### `lnk_streamer_channel`

| カラム | 型 | 説明 |
|---|---|---|
| `streamer_channel_hk` | CHAR(32) | `md5(streamer_hk || '~' || channel_hk)` |
| `streamer_hk` | CHAR(32) | FK → `hub_streamer.streamer_hk` |
| `channel_hk` | CHAR(32) | FK → `hub_channel.channel_hk` |
| `load_dts` | TIMESTAMP | |
| `rec_src` | VARCHAR | |

カーディナリティ: 1:N
````

### Snowflake DDL

```sql
CREATE OR REPLACE TABLE hub_streamer (
    streamer_hk      BINARY(16)         NOT NULL,
    streamer_id      VARCHAR             NOT NULL,
    load_dts         TIMESTAMP_NTZ       NOT NULL,
    rec_src          VARCHAR             NOT NULL,
    CONSTRAINT pk_hub_streamer PRIMARY KEY (streamer_hk)
);

CREATE OR REPLACE TABLE lnk_streamer_channel (
    streamer_channel_hk BINARY(16)       NOT NULL,
    streamer_hk         BINARY(16)       NOT NULL,
    channel_hk          BINARY(16)       NOT NULL,
    load_dts            TIMESTAMP_NTZ    NOT NULL,
    rec_src             VARCHAR          NOT NULL,
    CONSTRAINT pk_lnk_streamer_channel PRIMARY KEY (streamer_channel_hk),
    CONSTRAINT fk_lnk_sc_streamer  FOREIGN KEY (streamer_hk) REFERENCES hub_streamer(streamer_hk),
    CONSTRAINT fk_lnk_sc_channel   FOREIGN KEY (channel_hk)  REFERENCES hub_channel(channel_hk)
);
```

(注: Snowflake は FK 制約を保存するが、enforcement は既定で off。意図を
ドキュメント化する用途で記載)

### BigQuery DDL

```sql
CREATE OR REPLACE TABLE `project.dataset.hub_streamer` (
    streamer_hk    STRING       NOT NULL,
    streamer_id    STRING       NOT NULL,
    load_dts       TIMESTAMP    NOT NULL,
    rec_src        STRING       NOT NULL
)
CLUSTER BY streamer_hk;
```

(BigQuery は PK / FK 制約をサポートしないので clustering で代替。
Hash key は `TO_HEX(MD5(LOWER(TRIM(streamer_id))))` で 32 文字 hex として
保存する想定)

### dbt モデル雛形

```sql
-- models/raw_vault/hub_streamer.sql
{{
    config(
        materialized='incremental',
        unique_key='streamer_hk',
        on_schema_change='append_new_columns'
    )
}}

WITH source AS (
    SELECT * FROM {{ source('holodex', 'channels') }}
),

renamed AS (
    SELECT
        {{ dbt_utils.generate_surrogate_key(['lower(trim(channel_id))']) }} AS streamer_hk,
        channel_id                                              AS streamer_id,
        CURRENT_TIMESTAMP()                                     AS load_dts,
        'holodex_api'                                           AS rec_src
    FROM source
)

SELECT * FROM renamed

{% if is_incremental() %}
    WHERE streamer_hk NOT IN (SELECT streamer_hk FROM {{ this }})
{% endif %}
```

```sql
-- models/raw_vault/lnk_streamer_channel.sql
{{
    config(
        materialized='incremental',
        unique_key='streamer_channel_hk'
    )
}}

-- NOTE: source は「Streamer × Channel の対応関係を持つステージング層」を
-- 想定している。Holodex の場合、channels に owner_streamer_id 相当の
-- フィールドを staging で付与しておく必要がある。プロジェクトの実情に
-- 合わせて source 名と列名を置換すること。
WITH source AS (
    SELECT
        streamer_id,    -- domain (Streamer) のビジネスキー
        channel_id      -- range (Channel) のビジネスキー
    FROM {{ source('holodex_staging', 'streamer_channel_map') }}
),

hashed AS (
    SELECT
        {{ dbt_utils.generate_surrogate_key([
            'lower(trim(streamer_id))',
            'lower(trim(channel_id))'
        ]) }}                                                       AS streamer_channel_hk,
        {{ dbt_utils.generate_surrogate_key(['lower(trim(streamer_id))']) }} AS streamer_hk,
        {{ dbt_utils.generate_surrogate_key(['lower(trim(channel_id))']) }}  AS channel_hk,
        CURRENT_TIMESTAMP()                                         AS load_dts,
        'holodex_api'                                               AS rec_src
    FROM source
)

SELECT * FROM hashed

{% if is_incremental() %}
    WHERE streamer_channel_hk NOT IN (SELECT streamer_channel_hk FROM {{ this }})
{% endif %}
```

(注: source の取り方とビジネスキー列名はプロジェクトごとに違う。雛形は
domain / range の双方が同じ source 行から取れる前提。Holodex のように
channel と streamer が事実上同居している場合と、別 source の場合とで
書き方が変わる)

## 例

### 例 1: Markdown で Hub だけ見たい

```text
User: 「VTuber の Hub 物理設計を Markdown で」

Claude:
  → mcp__metamesh__query_concept(sparql=<Hub 一覧の SPARQL>)
  → 6 Hub 取得 (Streamer / Channel / Stream / Organization / Clip / Topic)
  → Markdown 表で各 Hub のカラム定義を出力
  → 「Link も出す？DDL 形式に変える？」と提案
```

### 例 2: Snowflake DDL で全テーブル

```text
User: 「Snowflake DDL で全 Hub と Link を生成して」

Claude:
  → Hub + Link 両方の SPARQL 実行
  → Snowflake 規約 (BINARY(16), TIMESTAMP_NTZ, FK 制約あり) で DDL 生成
  → ```sql ブロックで一気に出力
  → 「dbt にも入れる？テスト定義も追加する？」
```

### 例 3: dbt 雛形

```text
User: 「dbt model 雛形を出して」

Claude:
  → Hub + Link 取得
  → dbt model SQL を 1 ファイル = 1 テーブル の単位で生成
  → source/ref の指定はプレースホルダ (例: source('holodex', 'channels'))
  → 「実際の source 名はあなたの dbt project に合わせて置換してね」と添える
```

## アンチパターン

- ❌ **オントロジーに無いビジネスキーを勝手に発明する** — `dv:business_key`
   が空の concept があった場合は **生成を中断**し、ユーザーに
   `mcp__metamesh__add_concept` でビジネスキーを追加するよう案内する。
   フォールバック (`<concept_id_snake>_id` で適当に埋める) は **絶対に
   しない**。間違ったキーで Hub を作ると下流が壊れる方が高コスト
- ❌ **audit columns (`load_dts` / `rec_src`) を省略する** — DV の根幹。
   どの形式でも必ず含める
- ❌ **Sat (Satellite) テーブルを勝手に生成する** — descriptive attributes
   のオントロジー化はまだ無い (`add_attribute` ツール未実装)。Sat は
   「将来追加予定」と注釈にとどめ、生成しない
- ❌ **Multi-active Sat / PIT / Bridge / Reference テーブル** — 高度な DV 構成。
   ユーザーから明示要求が無い限り出さない (生成すると誤解を招く)
- ❌ **dbt 雛形でテストを勝手に追加する** — schema.yml のテスト
   (uniqueness, not_null, relationships) も将来の作業として案内するに
   とどめる。実装は別 Skill / 手動
- ❌ **Hash key の入力前処理を省略する** — `lower(trim(...))` を必ず通す。
   省略すると "ABC " と "abc" が別 hash になり、整合性が壊れる
- ❌ **どの DDL 方言か聞かずに決める** — Snowflake / BigQuery /
   汎用 SQL は型・関数が違う。明示確認を取る
