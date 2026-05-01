---
name: cbc-modeling-interview
description: ユーザーが metamesh オントロジーに新しいビジネス概念を定義したい・ドメインモデリングを始めたい・業務語彙を構造化メタデータとして残したいとき、Ensemble Logical Modeling (Data Vault 系) の Core Business Concept (CBC) Form を模した構造化インタビューを実施し、`mcp__metamesh__add_concept` MCP ツールで永続化する Skill。トリガー例: 「新しい概念を定義したい」「ドメインモデリングを始めたい」「X って概念を追加して」「オントロジーに entity を入れたい」。
---

# CBC (概念) モデリングインタビュー

ビジネス概念 1 件を構造化インタビューで聞き取り、SKOS JSON-LD として
`mcp__metamesh__add_concept` で永続化する Skill。

質問項目は **Ensemble Logical Modeling (Data Vault 系) の Core Business
Concept (CBC) Form** を下敷きにしている。狙いは、人間の頭の中に閉じ込め
られている同義語・階層・物理実装意図といったメタデータを **下流に流れる前
に明示的に抽出する** こと (PROJECT_CONTEXT.md §1.2 第①断絶点への対処)。

## 前提条件

- metamesh MCP server が接続済みであること。`mcp__metamesh__add_concept`
  が呼び出せれば OK。
- 似た概念が既にオントロジー内に存在する可能性がある場合、新規作成の前に
  `mcp__metamesh__query_concept` (keyword モード) で重複・近似を先に
  確認する。

## インタビューの流れ

下表の質問を上から順番に投げる。**必須** 項目は必ず答えてもらい、**推奨/
任意** 項目はユーザーが「skip」「なし」または無言ならスキップしてよい。
**9 問を 1 メッセージで束ねて投げない** こと — 1 問ずつ、回答に応じて
追質問を具体化していく。

| # | フィールド | 必須? | 質問 (ja) | ツール引数 |
|---|---|---|---|---|
| 1 | `concept_id` | ✅ | "URI として使う英語名は？(PascalCase 推奨。例: Streamer / Customer / OrderLine)" | `concept_id` |
| 2 | `pref_label_ja` | ✅ | "日本語での正式名称は？(例: 配信者)" | `pref_label_ja` |
| 3 | `definition_ja` | ✅ | "1〜2 文で何を表す概念か説明してください" | `definition_ja` |
| 4 | `pref_label_en` | 推奨 | "英語での正式名称は？(skip 可)" | `pref_label_en` |
| 5 | `definition_en` | 推奨 | "英訳の定義文があれば教えてください (skip 可)" | `definition_en` |
| 6 | `alt_labels_ja` / `alt_labels_en` | 推奨 | "他に呼ばれる名前は？(別表記・略称・英訳・社内用語など全部)" | `alt_labels_ja`, `alt_labels_en` |
| 7 | `broader` / `narrower` / `related` | 任意 | "上位概念・下位概念・関連概念があれば教えてください" | `broader`, `narrower`, `related` |
| 8 | `extension` (DV/Kimball) | 任意 | "Data Vault で実装するなら Hub？Link？business_key になる属性は？(Kimball なら Dimension/Fact、SCD Type)" | `extension={namespace, data}` |
| 9 | `scheme` | 任意 | "所属する Concept Scheme があれば (例: VTuberDomain)" | `scheme` |

### なぜ日本語と英語の両方を聞くか

英訳・別表記・社内用語の差分は **§1.3 で挙げた「同義語が AI に届かない」問題
の元凶**。「得意先」「顧客」「Customer」「Account」が同じ概念だと AI が
知らないと、そもそも検索クエリが合致しない。`alt_labels` は雑にでも全部入れる
価値がある。

### なぜ DV/Kimball メタデータは任意か

オントロジー自体は方法論非依存 (W3C 標準だけで完結) が原則
(PROJECT_CONTEXT.md §2.2)。DV/Kimball 拡張は「将来の物理実装のヒント」として
残すもので、まだ決まってないなら飛ばしてよい。後から
`mcp__metamesh__add_concept` を呼び直せば上書きできる。

## インタビュー後の流れ

1. **重複チェック**: 入力された `concept_id` と類似する既存概念がないか
   `mcp__metamesh__query_concept` で確認 (keyword モードで `concept_id` と
   `pref_label_ja` を投げる)
2. **登録**: `mcp__metamesh__add_concept` を呼ぶ。引数は会話で集めた値を
   そのまま渡す
3. **確認**: 保存されたファイルパスをユーザーに見せる
   (例: `Saved: /path/to/ontology/concepts/Streamer.jsonld`)
4. **次の一手**: 関係性 (NBR) もモデリングするか聞く。YES なら
   `nbr-identification` Skill を案内する

## 例

### 最小例

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

### DV マッピング含む完全例

```text
User: 「コラボの概念を作りたい」

Claude: (重複チェック) "コラボ" で mcp__metamesh__query_concept → 既存 0 件
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

## アンチパターン

- ❌ 9 個の質問を 1 メッセージで投げない (圧迫感、答える気を削ぐ)
- ❌ 既存類似概念を確認せずに新規作成する (オントロジーの分裂)
- ❌ `alt_labels` をスキップする (これがある/ないでオントロジーの実用性が大きく変わる)
- ❌ DV/Kimball 拡張を強制する (方法論固有のヒント、未決でよい)
- ❌ 概念を保存後に何もアナウンスしない (ファイルパスを見せて、次の一手を提示する)
