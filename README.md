# metamesh

> モデルストーミング（DV / Dimensional）で生まれるビジネスメタデータを、
> W3C 標準（SKOS / OWL / JSON-LD）でローカルに構造化し、
> セマンティックレイヤーと AI エージェントへ自動配信する MCP サーバー OSS。

## 位置づけ

- **Single Source of Truth** = 標準フォーマットのオントロジー（独自フォーマットは作らない）
- **Claude 自身がインテーク機能になる** — ユーザーが SKOS を知らなくても、Claude がインタビュー形式で概念定義を引き出し JSON-LD に永続化する
- **下流伝播は単方向** — オントロジー → dbt YAML / Semantic Layer / LLM コンテキスト

詳細は `docs/PROJECT_CONTEXT.md` を参照。

## ロードマップ

| Step | スコープ | 状態 |
|---|---|---|
| 1 | `add_concept` ツール (Claude インタビュー → `ontology/concepts/*.jsonld`) | **着手中** |
| 2 | `add_relationship` / `generate_dbt_yaml` | 未着手 |
| 3 | `generate_semantic_layer` / VTuber 分析基盤への実適用 | 未着手 |

## 技術スタック

- Python 3.11+
- [`mcp`](https://github.com/modelcontextprotocol/python-sdk) (`FastMCP`)
- [`rdflib`](https://github.com/RDFLib/rdflib) — RDF/SKOS/OWL 操作
- [`pyld`](https://github.com/digitalbazaar/pyld) — JSON-LD 正規化
- 依存管理: [`uv`](https://github.com/astral-sh/uv)

## 開発手順

```bash
# 依存インストール
uv sync

# サーバー起動 (stdio)
uv run python -m metamesh.server

# テスト
uv run pytest
```

## Claude Desktop への登録

`~/Library/Application Support/Claude/claude_desktop_config.json` に追記:

```json
{
  "mcpServers": {
    "metamesh": {
      "command": "uv",
      "args": ["--directory", "/Users/iwashita/metadata_oss/metamesh", "run", "python", "-m", "metamesh.server"]
    }
  }
}
```

## ディレクトリ構成

```
metamesh/
├── src/metamesh/
│   ├── server.py              # FastMCP エントリ
│   ├── tools/add_concept.py   # MVP ツール
│   └── ontology/store.py      # JSON-LD 永続化
├── ontology/
│   ├── concepts/              # SKOS 概念ファイル (SSoT)
│   └── relationships/         # OWL ObjectProperty 群
├── tests/
└── docs/
    ├── PROJECT_CONTEXT.md     # 設計の根拠 (権威)
    └── references/            # 参考資料へのポインタ
```
