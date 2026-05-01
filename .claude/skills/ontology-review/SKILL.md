---
name: ontology-review
description: ユーザーが metamesh オントロジーの品質チェック・整合性検証・健康診断を求めたとき — オーファン概念・定義欠落・参照切れ・DV 拡張漏れ・命名規約違反などを SPARQL で機械的に検出し、指摘リストを Markdown で返す read-only 診断 Skill。`mcp__metamesh__query_concept` を使うのみで、概念・関係性は一切変更しない。トリガー例: 「オントロジーをレビューして」「整合性チェック」「孤立した概念ある？」「定義が抜けてる concept 探して」「ontology の health check」。
---

# オントロジーレビュー (read-only 診断)

オントロジーが育つにつれて発生しがちな品質問題を、**SPARQL クエリだけで**
網羅的に検出する Skill。データには一切手を触れない (read-only)。

検出する問題の典型例:
- **オーファン概念**: relationship からも `skos:related` からも参照されていない孤立 concept
- **定義欠落**: `skos:definition` が無い concept / relationship
- **同義語欠落**: `skos:altLabel` が無い concept (= §1.3 の同義語問題が将来発生する火種)
- **参照切れ**: relationship の `rdfs:domain` / `rdfs:range` が存在しない concept を指している
- **DV/Kimball 拡張漏れ**: `dv:hub` / `dv:link` も `kimball:dimension` も無い concept
- **命名規約違反**: relationship_id が PascalCase, concept_id が lower_snake になっている等

## 前提条件

- `mcp__metamesh__query_concept` が利用可能 (SPARQL SELECT / ASK モード)
- 副作用ゼロ。`mcp__metamesh__add_concept` / `mcp__metamesh__add_relationship` は一切呼ばない

## 診断チェックの SPARQL レシピ

### 1. オーファン概念 (誰からも参照されていない concept)

```sparql
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?concept ?label WHERE {
    ?concept a skos:Concept .
    OPTIONAL { ?concept skos:prefLabel ?label . FILTER(LANG(?label) = "ja") }
    FILTER NOT EXISTS { ?_rel rdfs:domain ?concept }
    FILTER NOT EXISTS { ?_rel rdfs:range ?concept }
    FILTER NOT EXISTS { ?_other skos:related ?concept }
    FILTER NOT EXISTS { ?concept skos:related ?_other }
    FILTER NOT EXISTS { ?_other skos:broader ?concept }
    FILTER NOT EXISTS { ?concept skos:broader ?_other }
}
ORDER BY ?concept
```

「孤立 = 何にも繋がってない」概念を抽出。`true` 孤立か、定義漏れによる
未接続かは人間判断。

### 2. 定義欠落 (skos:definition が無い)

```sparql
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT ?id ?type WHERE {
    {
        ?id a skos:Concept .
        BIND("concept" AS ?type)
    } UNION {
        ?id a owl:ObjectProperty .
        BIND("relationship" AS ?type)
    }
    FILTER NOT EXISTS { ?id skos:definition ?_def }
}
ORDER BY ?type ?id
```

定義が無い概念は AI が意味理解できない最大の障害。優先度高めで指摘。

### 3. 同義語欠落 (skos:altLabel が無い concept)

```sparql
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?concept ?label WHERE {
    ?concept a skos:Concept ;
             skos:prefLabel ?label .
    FILTER(LANG(?label) = "ja")
    FILTER NOT EXISTS { ?concept skos:altLabel ?_alt }
}
ORDER BY ?concept
```

`altLabel` が無い = 別表記・社内用語・英訳が登録されてない = 将来の検索で
ヒットしない火種。**Major の警告**として報告。

### 4. 参照切れ (domain / range が存在しない concept を指す)

```sparql
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?relationship ?missing_target ?role WHERE {
    {
        ?relationship rdfs:domain ?missing_target .
        BIND("domain" AS ?role)
    } UNION {
        ?relationship rdfs:range ?missing_target .
        BIND("range" AS ?role)
    }
    FILTER NOT EXISTS { ?missing_target a skos:Concept }
}
ORDER BY ?relationship
```

これに該当があると **Critical**。物理実装で必ず壊れる。即修正。

### 5. DV/Kimball 拡張漏れ

```sparql
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dv: <https://metamesh.dev/ext/dv/>
PREFIX kimball: <https://metamesh.dev/ext/kimball/>

SELECT ?concept ?label WHERE {
    ?concept a skos:Concept .
    OPTIONAL { ?concept skos:prefLabel ?label . FILTER(LANG(?label) = "ja") }
    FILTER NOT EXISTS { ?concept dv:hub ?_h }
    FILTER NOT EXISTS { ?concept dv:link ?_l }
    FILTER NOT EXISTS { ?concept kimball:dimension ?_d }
    FILTER NOT EXISTS { ?concept kimball:fact ?_f }
}
ORDER BY ?concept
```

物理実装の hint が無い = 下流生成 (`generate_dbt_yaml` / `generate_semantic_layer`)
で「naming は snake_case fallback、PK は推測」になる。**意図的なら OK**
(例: `Collaboration` のような pure SKOS 概念) なので、Info レベルで報告。

### 6. 命名規約違反

```sparql
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

# concept_id は PascalCase 推奨。先頭が小文字 / アンダースコアを含む = 違反
SELECT ?concept WHERE {
    ?concept a skos:Concept .
    FILTER(REGEX(STRAFTER(STR(?concept), "/ontology/"), "^[a-z]|_"))
}

# relationship_id は lower_snake 推奨。大文字を含む = 違反
SELECT ?relationship WHERE {
    ?relationship a owl:ObjectProperty .
    FILTER(REGEX(STRAFTER(STR(?relationship), "/ontology/"), "[A-Z]"))
}
```

リネームは breaking change なので簡単じゃない (downstream 全部の参照を
更新する必要)。**Warning** で報告するに留め、修正は別課題化を推奨。

## 出力フォーマット

各チェックを順に走らせ、結果を以下の構造の Markdown で返す:

```markdown
# オントロジーレビュー結果

検査対象: 7 concepts, 6 relationships

## ✅ Critical (要即修正)
✅ 該当なし

## 🟠 Major (修正推奨)
- **[同義語欠落]** `Channel` (チャンネル) — altLabel 未登録。「YouTube チャンネル」「サブチャンネル」等を `mcp__metamesh__add_concept` で再登録すべし
- ...

## 🟡 Warning (検討)
- **[命名規約]** relationship `OwnsChannel` — PascalCase 検出、lower_snake (`owns_channel`) 推奨
- ...

## ℹ️ Info (参考)
- **[DV 拡張漏れ]** `Collaboration` — 意図的なら無視 (純 SKOS 概念として定義)
- ...
```

各項目には:
- **重要度ラベル** (絵文字 + 文字列)
- **チェック種別** (角括弧)
- **対象 ID** とラベル
- **次の一手** (具体的な修正 hint)

## 重要度の判断基準

| Severity | 例 | 対処 |
|---|---|---|
| ✅ Critical | 参照切れ (domain/range が存在しない) | 即修正、放置すると downstream で必ず壊れる |
| 🟠 Major | 定義欠落、同義語欠落 | 早めに修正。AI 利用時に意味が伝わらない |
| 🟡 Warning | 命名規約違反 | 既存参照との互換考慮、別 PR で計画的に |
| ℹ️ Info | DV/Kimball 拡張漏れ | 意図的かどうか確認、必要なら拡張追加 |

## 例

### 例 1: 全体ヘルスチェック

```text
User: 「オントロジーをレビューして」

Claude:
  → 6 つのチェック SPARQL を順に実行
    - mcp__metamesh__query_concept(sparql=<オーファン>)
    - mcp__metamesh__query_concept(sparql=<定義欠落>)
    - ... (4 つ続く)
  → 結果を Severity 別に集計
  → 上記フォーマットで Markdown 返答
```

### 例 2: 特定チェックのみ

```text
User: 「定義抜けてる concept だけ見せて」

Claude:
  → 「定義欠落」チェックの SPARQL のみ実行
  → 該当が空なら "✅ 全 concept に definition あり" と返す
  → あれば list で返し、それぞれ "次の一手" として mcp__metamesh__add_concept の呼び方例を添える
```

## 可視化との連携

オーファン概念や参照切れを発見した場合、`ontology-visualize` Skill と
組み合わせて「該当箇所だけのフォーカスグラフ」を見せると修正方針が決めやすい:

> 「Streamer 周辺だけ Mermaid で見せて」 → ontology-visualize Skill 起動 → 修正前後の対比に使える

## アンチパターン

- ❌ **診断結果を絶対視する** — Severity ラベルは目安。「DV 拡張漏れ」は
   意図的な場合 (純 SKOS 概念) も多いので、機械的に「修正必須」扱いしない
- ❌ **このスキルからオントロジーを書き換えない** — read-only。修正は
   `cbc-modeling-interview` / `nbr-identification` で人間が判断して行う
- ❌ **SPARQL 結果が空の時に何も返さない** — 「✅ 該当なし」を明示的に
   出すこと。判定済みであることを伝えるのが review の半分の価値
- ❌ **6 つ全部のチェックを毎回フル実行する** — 大規模オントロジーで遅い。
   ユーザーが特定種類だけ知りたいなら該当 SPARQL のみ実行
- ❌ **修正案を勝手に実行する** — 必ず「こう修正してはどうですか」と
   提案までで止め、実行はユーザー承認後 (= 別 Skill 起動)
