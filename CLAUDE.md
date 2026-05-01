# metamesh — Claude 作業指針

このファイルは Claude Code / Desktop が metamesh リポジトリで作業するときに
参照する指針。設計の根拠は `docs/PROJECT_CONTEXT.md` を Single Source of
Truth として参照すること。

## このプロジェクトについて

**「モデルストーミングで生まれるビジネスメタデータを W3C 標準オントロジーで
構造化し、MCP 経由で Claude が直接読み書きすることで、dbt / Semantic Layer
/ AI に同じ意味を届ける OSS」**

ユーザー向け概要・使い方は `README.md` を参照。本ファイルは内部実装方針。

## 言語

- 開発者は日本人。説明・コミット・ドキュメントは日本語。
- コード・識別子・W3C 用語（skos:Concept など）は英語のまま。

## アーキテクチャ原則

1. **MCP は薄く、データは厚く** — 書き込み 2 (`add_concept`,
   `add_relationship`) / 読み取り 1 (`query_concept`) が core。
   残りの generator は optional な bulk export で、通常は client 側
   (Claude / Skill) が SPARQL で都度合成すれば足りる
2. **ワークフローは Skills へ** — CBC インタビュー・NBR 設計・DV 実装方針
   などはコードに固めず `.claude/skills/<name>/SKILL.md` として配布
3. **下流伝播は単方向** — オントロジー → dbt YAML / Semantic Layer / LLM
   コンテキスト。逆流禁止 (生成された YAML を編集しても SSoT には反映されない)
4. **独自フォーマット禁止** — SKOS/OWL/JSON-LD で表現できないものは諦める
   か、`dv:` / `kimball:` 拡張 namespace に閉じ込める

## 名前空間

- ベース: `https://metamesh.dev/ontology/`
- DV 拡張: `https://metamesh.dev/ext/dv/`
- Kimball 拡張: `https://metamesh.dev/ext/kimball/`

これらは `src/metamesh/ontology/store.py` の `BASE_NS` / `EXT_NS` 定数。
変更すると既存の jsonld ファイルとの URI 互換が壊れるので慎重に。

## ディレクトリ構成

```
metamesh/
├── src/metamesh/
│   ├── server.py                # FastMCP エントリ。6 ツールの登録
│   ├── ontology/store.py        # ConceptStore: JSON-LD 永続化 + rdflib round-trip 検証
│   ├── tools/                   # MCP ツール (1 ファイル 1 ツール)
│   ├── generators/              # オントロジー → 下流フォーマットの pure 変換関数
│   │   └── _common.py           # snake_case / label_for_lang 等の共有ヘルパー
│   └── queries/concept.py       # keyword + SPARQL 検索
├── ontology/
│   ├── concepts/                # SKOS 概念 (SSoT)
│   └── relationships/           # OWL ObjectProperty
├── .claude/skills/              # Claude Skills (ワークフローガイド)
├── tests/                       # pytest (1 ツール = 1 ファイル目安)
├── output/                      # サンプル成果物 (再生成可、git 管理)
└── docs/
    ├── PROJECT_CONTEXT.md       # 設計の権威ドキュメント
    └── references/              # 参考文献ポインタ
```

## やってはいけないこと

- `ontology/concepts/*.jsonld` や `ontology/relationships/*.jsonld` を
  Claude が直接 Edit / Write しない。**必ず `add_concept` / `add_relationship`
  ツール経由で更新する** (rdflib round-trip 検証が走るため)
- 独自フォーマットの YAML / JSON を発明しない。SKOS / OWL に無い概念は
  `dv:` / `kimball:` 拡張に閉じ込める
- generator の出力を SSoT 扱いしない。常にオントロジー → 生成物の単方向
- `output/` 以下を手で編集しない (再生成すれば消える前提)

## テスト方針

- ユニットテストは `tests/`。**1 MCP ツール = 1 テストファイル** が目安
- JSON-LD は rdflib でパースして round-trip 検証する。生成物の文字列構造を
  直接 assert するとフォーマット変更で頻繁に壊れるため、トリプル単位や
  代表的な substring の含有で検証する
- 全テスト: `uv run pytest`
- 開発時は `uv sync --extra dev` で pytest / ruff も入れる

## 新ツール追加時のチェックリスト

1. `src/metamesh/tools/<name>.py` に `register(mcp, *, ontology_root)` 関数を作る
2. `src/metamesh/server.py` で import + 呼び出し
3. `tests/test_<name>.py` で振る舞いをカバー
4. README.md の「MCP ツール一覧」を更新
5. ツールが「core」か「optional bulk exporter」かを明記
6. **MCP server は long-running process** なので、コード追加後は Claude
   Desktop / Code を再起動しないと新ツールが認識されない (ユーザー向け
   注意点)

## 新 Skill 追加時のチェックリスト

1. `.claude/skills/<skill-name>/SKILL.md` を作る (YAML frontmatter +
   Markdown 本文)
2. frontmatter の `description` には自然言語トリガーを必ず含める
   (例: 「"X したい" と言われたとき」)
3. metamesh MCP ツールを使うときは `mcp__metamesh__<tool>` のフルネームで
   参照する
4. アンチパターン (やってはいけない使い方) を明記する
5. README.md のロードマップ表に追加
