# metamesh

> モデルストーミング（DV / Dimensional）で生まれるビジネスメタデータを
> **W3C 標準 (SKOS / OWL / JSON-LD)** で 1 箇所に保存し、
> **MCP 経由で Claude が直接読み書き** することで、
> dbt / Semantic Layer / AI/LLM すべてに同じ意味を届ける OSS。

## 解こうとしている問題

データ基盤の下流に行くほど **ビジネスメタデータ（人間の頭の中の知識）が削られていく**。

```
モデルストーミング成果物 (情報量 100%)
  → DV/Mart 実装        (情報量 30%: 定義が削れる)
    → Semantic Layer    (情報量 15%: ビジネス定義が消える)
      → Data Catalog    (情報量 10%)
        → AI / LLM      (情報量  5%: 構造は分かるが意味が分からない)
```

「得意先別売上」と「顧客別売上」が同じクエリにならない、配信者と
チャンネルとサブチャンネルの関係が AI に伝わらない、といった現象は、
**5 つの断絶点** で同義語・階層・関係性の意味・実装の対応がそれぞれ
失われることが原因。

詳細: [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md)（フレームワーク
全体）。

## metamesh の設計思想

| 原則 | 帰結 |
|---|---|
| **Single Source of Truth = W3C 標準のオントロジー** | 独自フォーマットは作らない。`ontology/concepts/*.jsonld` と `ontology/relationships/*.jsonld` だけが信じる対象 |
| **MCP は薄く、データは厚く** | 書き込み 2 / 読み取り 1 が core。残りは optional な bulk export |
| **ワークフローは Skills へ** | CBC インタビュー・NBR 設計・DV 実装方針などは Claude Skills として配布。コードに固めない |
| **下流生成はクライアント側で都度合成** | 「Mermaid で可視化」「dbt schema.yml に変換」は Claude が SPARQL で取って即時生成すれば済む |

## 構成要素

```
┌──────────────────────────────────────────────────┐
│  ユーザー (データエンジニア / 研究者)               │
│       ↕ 自然言語                                   │
│  Claude Desktop / Code                            │
│  ├─ Skills (.claude/skills/)                       │
│  │  ├─ cbc-modeling-interview                      │
│  │  ├─ nbr-identification                          │
│  │  └─ ontology-visualize                          │
│  │     (ontology-review, dv-implementation-design   │
│  │      は今後追加予定)                              │
│       ↕ MCP                                        │
│  metamesh server  (薄い primitive)                 │
│  ├─ Write : add_concept, add_relationship          │
│  └─ Read  : query_concept (SPARQL: SELECT/         │
│              CONSTRUCT/DESCRIBE/ASK)               │
│       ↕                                            │
│  ontology/  (SKOS/OWL/JSON-LD = SSoT, Git 管理)    │
└──────────────────────────────────────────────────┘
```

## クイックスタート

### 1. 依存インストール

```bash
git clone https://github.com/Islanders-Treasure0969/metamesh.git
cd metamesh
uv sync --extra dev
uv run pytest          # 動作確認 (69 tests)
```

### 2. Claude Desktop に登録

`~/Library/Application Support/Claude/claude_desktop_config.json` に追記:

```json
{
  "mcpServers": {
    "metamesh": {
      "command": "/path/to/uv",
      "args": [
        "--directory", "/path/to/metamesh",
        "run", "python", "-m", "metamesh.server"
      ]
    }
  }
}
```

`uv` のフルパスは `which uv` で取得（PATH を継承しない環境があるため絶対パス推奨）。

### 3. 最初の概念を作る

Claude にこう話しかけるだけ:

```
「Streamer って概念を metamesh に追加して」
```

`cbc-modeling-interview` Skill が起動して、Claude が CBC Form 相当の質問を
順番に投げてくれる。回答すれば自動的に `ontology/concepts/Streamer.jsonld`
が生成される。

## MCP ツール一覧

### Core (3)

書き込みと検索の最小セット。**通常はこれだけで完結する**。

| Tool | 用途 |
|---|---|
| `add_concept` | 概念 (skos:Concept) を 1 件登録。多言語ラベル・同義語・階層・関連・DV/Kimball 拡張に対応 |
| `add_relationship` | 関係性 (owl:ObjectProperty) を 1 件登録。domain / range / 逆関係 / 拡張 |
| `query_concept` | キーワード or SPARQL で検索。SPARQL は SELECT / CONSTRUCT / DESCRIBE / ASK をサポート |

### Optional bulk exporters (3)

CI で一括書き出しする等の用途には便利。**通常運用では `query_concept` で
都度引いて Claude が必要な形に変換すれば足りる**ので、必須ではない。

| Tool | 用途 |
|---|---|
| `generate_dbt_yaml` | オントロジー → `schema.yml` (description + meta) |
| `generate_semantic_layer` | オントロジー → MetricFlow YAML (semantic_models + entities) |
| `export_llm_context` | オントロジー → Markdown digest (LLM プロンプト貼付用) |

サンプル出力: [`output/dbt/schema.yml`](output/dbt/schema.yml) / 
[`output/semantic_layer/metricflow.yml`](output/semantic_layer/metricflow.yml) /
[`output/llm_context/context.md`](output/llm_context/context.md)

## SPARQL 実例集

`query_concept(sparql=...)` で叩ける。CONSTRUCT / DESCRIBE は subgraph を
triples で返すので、Claude が即座に Mermaid やテーブルに変換可能。

### 全 Hub と business_key を一覧

```sparql
PREFIX dv: <https://metamesh.dev/ext/dv/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT ?label ?hub ?bk WHERE {
    ?c dv:hub ?hub ;
       dv:business_key ?bk ;
       skos:prefLabel ?label .
    FILTER(LANG(?label) = "ja")
}
ORDER BY ?hub
```

### 特定概念の近傍 subgraph (CONSTRUCT)

```sparql
CONSTRUCT { ?s ?p ?o }
WHERE {
    { <https://metamesh.dev/ontology/Streamer> ?p ?o . BIND(<https://metamesh.dev/ontology/Streamer> AS ?s) }
    UNION
    { ?s ?p <https://metamesh.dev/ontology/Streamer> . BIND(<https://metamesh.dev/ontology/Streamer> AS ?o) }
}
```

→ Claude が triples を Mermaid に変換して即時可視化。

### N:M 関係性だけ抽出

```sparql
PREFIX dv: <https://metamesh.dev/ext/dv/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?rel ?domain ?range WHERE {
    ?rel dv:cardinality "N:M" ;
         rdfs:domain ?domain ;
         rdfs:range ?range .
}
```

## 可視化について

**metamesh は組み込みの可視化コマンドを持たない**。理由:

1. SPARQL (CONSTRUCT) で subgraph を取れば、Claude が文脈に応じた最適な
   形式 (Mermaid / Graphviz / 表 / Cytoscape JSON) で都度レンダリングできる
2. オントロジー編集の標準ツール ([Protégé](https://protege.stanford.edu/) /
   [WebVOWL](http://vowl.visualdataweb.org/webvowl.html)) は metamesh の
   出力する JSON-LD を直接食える。深い分析はそちらに任せた方が劣化しない

この設計の具体実装が `ontology-visualize` Skill。「Mermaid で見せて」「N:M
関係だけ図示して」「Streamer 周辺だけ」等の自然言語要求を SPARQL CONSTRUCT
に変換 → triples を Mermaid に変換 → チャットに直貼り、を 1 プロンプトで
完結する。`.claude/skills/ontology-visualize/SKILL.md` 参照。

## オントロジー直接編集 (advanced)

オントロジーは生 JSON-LD ファイルなので、好きなツールで開いて手で書ける:

- **Protégé** で `ontology/concepts/*.jsonld` を順次 import
- **WebVOWL** に JSON-LD をアップロードして可視化
- 任意のテキストエディタ + git diff レビュー

`add_concept` / `add_relationship` は rdflib で round-trip 検証してから
保存するので、これらツール経由で書いた場合は別途整合性確認を推奨
(`uv run pytest` で構造テスト)。

## 実証ドメイン: VTuber 分析基盤

`ontology/` には [Holodex API](https://holodex.stoplight.io/) を想定した
**VTuber 分析の初期オントロジー** が入っている:

- 7 概念: `Streamer` / `Channel` / `Stream` / `Organization` / `Collaboration` / `Clip` / `Topic`
- 6 関係性: `owns_channel` / `hosts_stream` / `belongs_to_org` / `participates_in` / `derived_from` / `categorized_as`
- 13 個の DV Hub/Link 候補が `dv:` 拡張で記録済み

これをそのまま下流ツールに流せば、`output/` 以下の 3 つのサンプル成果物が再生成できる。

## 開発

```bash
uv sync --extra dev    # ruff / pytest / pytest-asyncio
uv run pytest -v       # 69 tests (= 6 add_concept + 7 add_relationship +
                       #  15 query_concept + 11 generate_dbt_yaml +
                       #  9 generate_semantic_layer + 15 export_llm_context +
                       #  6 SPARQL form coverage)
uv run ruff check .
```

## ロードマップ

| Step | スコープ | 状態 |
|---|---|---|
| 1 | `add_concept` ツール | ✅ |
| 2 | `add_relationship` / `generate_dbt_yaml` | ✅ |
| 3a | `generate_semantic_layer` / `export_llm_context` / `query_concept` | ✅ |
| 3b | `cbc-modeling-interview` Skill | ✅ |
| 3c | `nbr-identification` Skill | ✅ |
| 3d | `ontology-visualize` Skill | ✅ |
| 4 | 追加 Skills (`ontology-review`, `dv-implementation-design`) | 未着手 |
| 5 | Holodex API 実データでの検証 | 未着手 |
| 6 | SHACL バリデーション | 未着手 |
| 7 | `add_metric` (MetricFlow メトリクス定義のオントロジー化) | 未着手 |

## 関連資料

- [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md) — フレームワーク全体の設計根拠
- [`docs/references/`](docs/references/) — Data Vault / SKOS / OWL の参考資料

## License

Apache-2.0
