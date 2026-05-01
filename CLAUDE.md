# metamesh — Claude 作業指針

## このプロジェクトについて

**「モデルストーミングで生まれるビジネスメタデータを W3C 標準オントロジーで構造化し、
セマンティックレイヤーと AI に自動配信する MCP サーバー OSS」**

設計の根拠は `docs/PROJECT_CONTEXT.md` を Single Source of Truth として参照すること。

## 言語

- 開発者は日本人。説明・コミット・ドキュメントは日本語。
- コード・識別子・W3C 用語（skos:Concept など）は英語のまま。

## 現在のスコープ (Step 1 MVP)

- `add_concept` ツールのみ実装
- Claude がチャットでインタビュー → 引数を組み立てて 1 回呼び出し
- `ontology/concepts/{concept_id}.jsonld` に SKOS 形式で保存
- Claude Desktop から動作確認できること

**Step 2 以降のツール (`add_relationship`, `generate_dbt_yaml` 等) はまだ実装しない。**
スコープ拡大の前に必ず確認すること。

## 設計原則 (PROJECT_CONTEXT.md §2 より)

1. **Single Source of Truth = 標準フォーマット**。独自 YAML を発明しない
2. **コアと拡張の分離**。SKOS/OWL がコア、DV/Kimball 固有は拡張名前空間
3. **変更は単方向伝播**。オントロジー → 下流のみ。逆流禁止

## 名前空間

- ベース: `https://metamesh.dev/ontology/`
- DV 拡張: `https://metamesh.dev/ext/dv/`
- Kimball 拡張: `https://metamesh.dev/ext/kimball/`

これらは `src/metamesh/ontology/store.py` の定数にまとまっている。変更する場合は既存ファイルとの互換に注意。

## テスト

- ユニットテストは `tests/`
- JSON-LD は rdflib でパースして round-trip 検証する（生成物の構造をハードコードで assert しない）

## 参考資料

`docs/references/README.md` に `/Users/iwashita/practical_data_vault/` 内の関連章へのポインタあり。
特に以下が設計の出発点:
- `chapter_12_design_process.md` — モデルストーミング（CBC/NBR）
- `chapter_13_ontology_taxonomy.md` — DV と オントロジーの接続
- `research_part3_framework.md` — Ontology-Driven Metadata Pipeline

## やってはいけないこと

- 独自フォーマットの YAML / JSON を発明する（標準 SKOS/OWL を使う）
- `ontology/` 配下のファイルを Claude が直接編集する（必ず `add_concept` ツール経由）
- スコープ外のツール (`generate_*` 系) を未確認で実装する
