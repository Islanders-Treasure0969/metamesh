# 参考文献

metamesh の設計判断の元になっている文献群。詳細な設計議論は
`docs/PROJECT_CONTEXT.md` を参照。

## Data Vault モデリング (CBC / NBR)

CBC (Core Business Concept) Form と NBR (Natural Business Relationship)
Form は **Ensemble Logical Modeling (ELM)** という Data Vault 系の
モデリング手法に由来する。`add_concept` のインタビュー設計は CBC Form を、
`add_relationship` の引数設計は NBR Form をそれぞれ模している。

- **Hans Hultgren** _Modeling the Agile Data Warehouse with Data Vault_
  (Genesee Academy, 2012) — Ensemble Logical Modeling の原典。
  CBC/NBR フォームの定義
- **Daniel Linstedt & Michael Olschimke** _Building a Scalable Data
  Warehouse with Data Vault 2.0_ (Morgan Kaufmann, 2015) — DV 2.0 の
  Hub / Link / Satellite 物理設計
- **Daniel Linstedt** _Super Charge Your Data Warehouse_ (CreateSpace,
  2011) — Hash key / Audit column の元ネタ

## Dimensional モデリング (BEAM)

`generate_dbt_yaml` の "dim_" / "fct_" 命名や Kimball 拡張 namespace は
以下を想定。

- **Ralph Kimball & Margy Ross** _The Data Warehouse Toolkit, 3rd ed._
  (Wiley, 2013)
- **Lawrence Corr & Jim Stagnitto** _Agile Data Warehouse Design_
  (DecisionOne Press, 2011) — BEAM (Business Event Analysis & Modeling)
  と 7Ws フレームワーク

## オントロジー / セマンティックウェブ

metamesh の SSoT フォーマットは W3C 標準のみで構成する。

- **W3C** [SKOS Reference](https://www.w3.org/TR/skos-reference/) —
  概念定義の語彙 (skos:Concept / prefLabel / altLabel / definition / etc.)
- **W3C** [OWL 2 Web Ontology Language Primer](https://www.w3.org/TR/owl2-primer/) —
  ObjectProperty / domain / range / inverseOf
- **W3C** [JSON-LD 1.1](https://www.w3.org/TR/json-ld11/) — RDF の
  JSON シリアライゼーション (本リポジトリのファイル形式)
- **W3C** [SHACL](https://www.w3.org/TR/shacl/) — RDF の制約バリデーション
  (将来導入予定)

## Data Catalog / Metadata

- **DAMA International** _DMBOK 2_ (Technics Publications, 2017) —
  ビジネスメタデータ・テクニカルメタデータ・オペレーショナルメタデータの
  3 分類

## 既存ツール (互換ターゲット / 比較対象)

- **Protégé** — 標準的な OWL エディタ。metamesh の jsonld を直接
  import 可能。深い分析はこちらに委譲する設計
- **WebVOWL** — OWL 可視化。`http://vowl.visualdataweb.org/webvowl.html`
  に jsonld をアップロードすればグラフが見られる
- **dbt Semantic Layer (MetricFlow)** — `generate_semantic_layer` の出力先
- **dbt-core** — `generate_dbt_yaml` の出力先
- **MCP (Model Context Protocol)** — Claude Desktop / Code との
  通信プロトコル (本サーバーが実装)

## プロジェクト権威ドキュメント

- `docs/PROJECT_CONTEXT.md` — フレームワーク全体の問題提起・設計原則・
  技術選定の議論。設計判断に迷ったら最初に開く
