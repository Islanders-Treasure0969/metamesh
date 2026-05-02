# metamesh プロジェクト コンテキストドキュメント

> このドキュメントはClaude.aiでの議論を引き継ぐためのコンテキストです。
> Claude Desktop / Claude Code でこのファイルを読み込んで実装を開始してください。

> **読者向け注記 (重要)**:
> このドキュメントは metamesh フレームワークの設計議論を保存している。
> 本文中の **§4「実証テーマ：VTuber 分析基盤」と §6「次にやること」の VTuber
> 関連項目** は、設計の出発点としての記録であり、**実際の VTuber 実装は別
> リポジトリ
> [Islanders-Treasure0969/vtuber-analytics](https://github.com/Islanders-Treasure0969/vtuber-analytics)
> に分離済み**。フレームワーク本体 (本リポジトリ) はドメイン非依存で、VTuber
> 固有のデータ・スクリプトは含まない。

---

## 0. このプロジェクトの一言説明

**「モデルストーミング（DV / Dimensional）で生まれるビジネスメタデータを構造化・管理し、
セマンティックレイヤーとAIエージェントに自動的に届けるMCPサーバーOSS」**

実証テーマ：VTuber（ホロライブ・にじさんじ）分析基盤
→ 実装は [vtuber-analytics](https://github.com/Islanders-Treasure0969/vtuber-analytics) に分離

---

## 1. 問題意識（研究の出発点）

### 1.1 解決したい問題

データ基盤にはデータとメタデータの2つの流れがあるが、
**ビジネスメタデータ（人間の頭の中にある知識）が下流に届かない**。

```
モデルストーミング成果物（情報量100%）
  → DV/Mart実装（情報量30%：定義が簡略化）
    → Semantic Layer（情報量15%：計算式はあるがビジネス定義がない）
      → Data Catalog（情報量10%）
        → AI/LLM（情報量5%：構造は分かるが意味が分からない）
```

### 1.2 5つの断絶点

| 断絶点 | 場所 | 失われる情報 |
|---|---|---|
| ① | 概念設計 → DV実装 | 同義語・階層・関係性の意味・品質ルール |
| ② | DV実装 → Mart実装 | Hub→Dimの対応・変換ルールの理由 |
| ③ | Mart実装 → Semantic Layer | ビジネス定義・JPY換算済み等の変換情報 |
| ④ | Semantic Layer → Data Catalog | ビジネス定義・同義語・タクソノミー |
| ⑤ | Data Catalog → AI/LLM | オントロジー（概念階層・同義語・関係性の意味） |

### 1.3 具体例

「得意先別売上」と「顧客別売上」が同じクエリに変換されない
→ AIが同義語情報を持っていないから

### 1.4 ビジネスメタデータの3分類（DAMA-DMBOK準拠）

| 種別 | 内容 | 現状 |
|---|---|---|
| ビジネスメタデータ | 概念定義・同義語・階層・関係性・ルール | **人間の頭の中に閉じ込められている** |
| テクニカルメタデータ | テーブル・カラム・型・リネージュ | dbt docsで比較的管理されている |
| オペレーショナルメタデータ | 鮮度・品質テスト・処理ログ | dbt test・オーケストレーターで管理されている |

---

## 2. フレームワーク（Ontology-Driven Metadata Pipeline）

### 2.1 設計思想

**W3C標準（SKOS/OWL/JSON-LD）でオントロジーを1箇所に管理し、
それをSingle Source of Truthとして下流の全フェーズに伝播させる。**

```
オントロジー（SKOS/OWL/JSON-LD）= Single Source of Truth
    ↑ 入力（方法論非依存）
    ├── ELM/CBC/NBR Form（Data Vault系）
    ├── BEAM Table / 7Ws（Kimball系）
    └── Claude自身によるインタビュー ← metameshの核心

    ↓ 出力
    ├── dbt model YAML（description / meta）
    ├── MetricFlow / Semantic Layer YAML
    ├── Data Catalog Business Glossary
    └── AI/LLM コンテキスト（MCP経由）
```

### 2.2 3つの原則

1. **Single Source of Truth = 標準フォーマットのオントロジー**（独自フォーマットは作らない）
2. **コアと拡張の分離**（方法論非依存のコア SKOS/OWL ＋ DV/Kimball固有の拡張名前空間）
3. **変更の単方向伝播**（オントロジー → 下流、逆方向は禁止）

### 2.3 使用するW3C標準

```
RDF（基盤）
├── SKOS（概念定義の中心）
│   ├── skos:Concept        → 概念
│   ├── skos:prefLabel      → 優先名称（言語別）
│   ├── skos:altLabel       → 同義語（得意先, Account等）
│   ├── skos:definition     → 定義文
│   ├── skos:broader/narrower → 階層構造
│   └── skos:exactMatch     → 異システム間の同一概念
├── OWL（関係性の制約）
│   ├── owl:ObjectProperty  → 関係性の型
│   ├── owl:Restriction     → カーディナリティ（1:N等）
│   └── owl:disjointWith    → 排他的サブタイプ
├── SHACL（バリデーション）
└── JSON-LD（シリアライゼーション形式）← ファイルの実形式
```

---

## 3. OSS設計（metamesh）

### 3.1 コンセプト

**Claude自身がインテーク機能になる。**

ユーザーが「配信者という概念を定義したい」と言うと、
Claudeが CBC Form相当の質問（定義は？同義語は？階層は？）を順番にして、
回答を自動的にSKOS/JSON-LDに変換してローカルファイルに保存する。

→ ユーザーがSKOSを知らなくても使える
→ Claude Desktop / Claude Code どちらでも動く
→ コミュニティが広く使えるOSSとして公開

### 3.2 アーキテクチャ

```
Claude Desktop / Claude Code
    ↕ MCP Protocol
┌──────────────────────────────────────┐
│  metamesh MCP Server                  │
│                                       │
│  ツール群                              │
│  ├── add_concept()                    │
│  │   Claudeがインタビューして概念を登録 │
│  ├── add_relationship()               │
│  │   概念間の関係性を定義               │
│  ├── query_concept()                  │
│  │   概念をSPARQL/キーワードで検索      │
│  ├── generate_dbt_yaml()              │
│  │   dbt model YAMLを自動生成         │
│  ├── generate_semantic_layer()        │
│  │   MetricFlow YAMLを自動生成        │
│  └── export_llm_context()            │
│      AIコンテキスト用Markdownを出力    │
└──────────────┬───────────────────────┘
               │ 読み書き
┌──────────────▼───────────────────────┐
│  ローカルファイルストア（Git管理可能）   │
│  ontology/                            │
│  ├── concepts/                        │
│  │   ├── streamer.jsonld              │
│  │   ├── stream.jsonld                │
│  │   ├── viewer.jsonld                │
│  │   └── superchat.jsonld             │
│  └── relationships/                   │
│      ├── streams_on.jsonld            │
│      └── collab_with.jsonld           │
└──────────────┬───────────────────────┘
               │ 生成
┌──────────────▼───────────────────────┐
│  出力アダプター                         │
│  ├── /output/dbt/models/             │
│  │   └── schema.yml（自動生成）        │
│  ├── /output/semantic_layer/         │
│  │   └── metrics.yml（自動生成）       │
│  └── /output/llm_context/            │
│      └── context.md（自動生成）        │
└──────────────────────────────────────┘
```

### 3.3 技術スタック候補

| 観点 | 候補A | 候補B |
|---|---|---|
| 言語 | Python（FastMCP） | TypeScript（MCP SDK） |
| JSON-LD処理 | `pyld` / `rdflib` | `jsonld` npm package |
| ストレージ | ローカルファイル（.jsonld） | ローカルファイル（.jsonld） |
| テスト | pytest | Jest |

→ **未決定。Claude Desktopでの議論で決める。**

### 3.4 MVPスコープ（Step 1）

**Step 1（最初に動かすもの）**
- `add_concept` ツールのみ実装
- Claude がインタビューして `ontology/concepts/*.jsonld` に保存
- Claude Desktop から実際に呼べること

**Step 2**
- `add_relationship` 追加
- `generate_dbt_yaml` 追加・実際のdbtプロジェクトで検証

**Step 3**
- `generate_semantic_layer` 追加
- VTuber分析基盤への実適用
- GitHub公開・コミュニティへ

---

## 4. 実証テーマ：VTuber分析基盤

### 4.1 なぜVTuberか

- 配信者・配信・コラボ・視聴者・スパチャなど**多様なビジネス概念**が存在する
- ホロライブ・にじさんじの**公開APIがある**
- メタ情報が豊富（配信者の属性・グループ・デビュー日・コラボ関係）
- Zennの読者（エンジニア）にも刺さるテーマ

### 4.2 データソース

| ソース | API | 取得できる情報 | 制限 |
|---|---|---|---|
| **Holodex API** | `api.holodex.net` | チャンネル・配信・切り抜き・コラボ関係・org別絞り込み | APIキー必要（無料） |
| **YouTube Data API v3** | Google Cloud | 動画メタデータ・チャンネル統計・コメント | 10,000units/日（無料） |

**方針：Holodex API メイン + YouTube Data API で補完**

Holodexで取れるもの：
```
- チャンネル情報（org, subscriber_count, english_name）
- 配信情報（title, status, start_scheduled, topic_id）
- コラボ情報（mentions: 一緒に出演した配信者）
- 切り抜き情報（どの配信者の切り抜きか）
```

### 4.3 分析基盤のターゲットアーキテクチャ

```
Holodex API / YouTube Data API
    ↓
Staging（dbt external tables or Python ingestion）
    ↓
Raw Vault（Hub: 配信者, 配信, 楽曲 / Link: コラボ, 出演）
    ↓
Business Vault（コラボ関係のビジネスルール適用）
    ↓
Information Mart（dim_streamer, dim_stream, fct_collab, fct_superchat）
    ↓
Semantic Layer（MetricFlow）
    ↓
分析エージェント（「人気VTuberのコラボ相関を分析して」）
```

### 4.4 モデルストーミングで定義すべき概念（初期候補）

```
CBC（Core Business Concepts）候補：
  - 配信者（Streamer）: VTuber個人
  - グループ（Organization）: ホロライブ, にじさんじ等
  - 配信（Stream）: 1回の配信イベント
  - コラボ（Collaboration）: 複数配信者が同時出演する配信
  - 視聴者（Viewer）: チャンネルの購読者・視聴者
  - スーパーチャット（Superchat）: 投げ銭イベント
  - 楽曲（Song）: オリジナル曲・カバー曲
  - 切り抜き（Clip）: 配信の一部を切り出した動画

NBR（Natural Business Relationships）候補：
  - 配信者 が 配信 を行う（1:N）
  - 配信者 が グループ に所属する（N:1）
  - 配信 に 複数の配信者 が 出演する（コラボ, N:M）
  - 配信者 が 楽曲 を 投稿する（N:M）
  - 視聴者 が 配信者 に スパチャ を 送る
  - 切り抜き は 配信 から 派生する（N:1）
```

---

## 5. Zenn Book構成草案

```
タイトル：
「メタデータから始めるAI分析基盤
 ─ VTuberデータで学ぶOntology-Driven Metadata Pipeline」
```

| 章 | タイトル | 内容 | 素材 |
|---|---|---|---|
| はじめに | — | 本書の目的・完成イメージ・対象読者 | 本会話の議論 |
| 第1章 | 問題提起 | メタデータの断絶・5つの断絶点 | research_part1 |
| 第2章 | 既存技術の整理 | 3フェーズ・ELM/BEAM・dbt MCP Serverの現在地 | research_part2 |
| 第3章 | フレームワーク | Ontology-Driven Metadata Pipeline・SKOS/OWL | research_part3 |
| 第4章 | OSS実装 | metameshの設計・MCPサーバー実装解説 | **これから作る** |
| 第5章 | VTuber分析基盤 | モデルストーミング→metamesh適用→エージェント分析 | **これから作る** |
| 第6章 | 考察と今後 | DEがオントロジーを扱う時代・metameshロードマップ | 本会話の議論 |

---

## 6. 次にやること（Claude Desktopでの実装開始）

### 優先順位

```
① metamesh の技術スタック決定（Python or TypeScript）
② Step 1 MVP実装：add_concept ツール
   - MCP サーバーのスキャフォールド
   - Claude インタビュー → JSON-LD保存 のフロー実装
   - Claude Desktop で動作確認
③ VTuber概念のモデルストーミング（metamesh自身を使って）
   - 「配信者」「配信」「コラボ」の3概念を先にやる
④ Holodex API でデータ取得スクリプト作成
⑤ dbt プロジェクトのスキャフォールド
```

### Claude Desktopへの指示（このファイルを渡した後）

```
PROJECT_CONTEXT.md を読んだ上で、以下を進めてください：

1. metamesh の技術スタック（Python FastMCP か TypeScript MCP SDK か）を
   メンテナビリティ・エコシステム・自分の使いやすさで提案してください

2. 決定後、Step 1 MVP の実装を開始してください
   - MCP サーバーのスキャフォールド
   - add_concept ツール（Claude がインタビューして JSON-LD に保存）
   - Claude Desktop での動作確認手順

3. 実装しながら、VTuber分析基盤のモデルストーミングも
   metamesh を使って実際に進めてください
```

---

## 7. 関連ファイル

| ファイル | 内容 |
|---|---|
| `research_part1_problem.md` | メタデータの断絶（問題提起） |
| `research_part2_current_state.md` | 既存技術の整理 |
| `research_part3_framework.md` | Ontology-Driven Metadata Pipelineフレームワーク |
| `research_part4_5_implementation_research.md` | 実装調査 |
| `book1/` | Data Vault基礎（Hash Keys, Audit Columns等） |
| `chapter_*.md` | DV × Ontology/Taxonomy 詳細章 |

---

## 8. キーワード・用語集

| 用語 | 説明 |
|---|---|
| metamesh | 本OSSのプロジェクト名（仮称） |
| Ontology-Driven Metadata Pipeline | 本フレームワークの名称（本研究による独自命名） |
| CBC Form | ELMワークショップでの概念定義フォーム（Core Business Concept） |
| NBR Form | ELMワークショップでの関係性定義フォーム（Natural Business Relationship） |
| BEAM Table | Kimball系のモデルストーミング成果物（7Ws分析） |
| SKOS | W3C標準のタクソノミー・シソーラス定義語彙 |
| OWL | W3C標準のオントロジー記述言語 |
| JSON-LD | RDFのJSONシリアライゼーション形式 |
| MetricFlow | dbt Semantic Layerの定義エンジン |
| Holodex API | VTuber特化のオープンAPI |
| セマンティックドリフト | 概念の定義が各フェーズで少しずつズレていく現象 |
| Single Source of Truth（SSoT） | ビジネス概念の定義の唯一の権威となるデータストア |

---

*作成日：2026-05-01 / Claude.ai での議論より*
