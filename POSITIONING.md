# metamesh の立ち位置

> 業務担当者と AI が同じ「業務概念の SSoT (Single Source of Truth)」を共有するための、
> モデルストーミング駆動のワークフロー OSS。

このドキュメントは「metamesh は何で、何ではないか」を 1 ページで示す。
詳細な技術仕様は [`README.md`](README.md) と [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md) を参照。

---

## 解こうとしている課題

データ基盤の各層で **ビジネスメタデータが 5 つの断絶点で削られていく**:

```text
モデルストーミング → DV/Mart 実装 → Semantic Layer → Data Catalog → AI/LLM
       100%              30%              15%             10%          5%
```

「得意先別売上」と「顧客別売上」が同じクエリにならない。配信者と
チャンネルとサブチャンネルの関係が AI に伝わらない。
個別の tool でこの問題を解いても、**断絶を再生産する別レイヤを増やすだけ** になる。

metamesh は、断絶の **手前 (モデルストーミング段階)** で生まれた業務概念の
意味・同義語・階層・関係性を W3C 標準で 1 箇所に保存し、下流の dbt /
Semantic Layer / Catalog / AI まで参照を届ける。

---

## 4 つの差別化ポイント

| # | 差別化 | 比較対象との違い |
|---|---|---|
| 1 | **モデルストーミング駆動** | 一般的な catalog (DataHub / OpenMetadata 等) は実装後の docs を集約する向き。metamesh は *実装前* の業務概念定義から始める |
| 2 | **W3C 標準 native** (SKOS / OWL / JSON-LD / SPARQL) | 独自スキーマや YAML だけの semantic layer 製品とは異なり、Linked Data エコシステム (Protégé / WebVOWL / GraphDB / Neo4j n10s) と直接連携できる |
| 3 | **MCP は薄く、ワークフローは Skills へ** | ロジックをサーバーに固めるのではなく、CBC / NBR / BEAM などのモデリング手法を Claude Skills として配布。Claude の文脈で対話的に動く |
| 4 | **下流フォーマットは合成、保存しない** | dbt schema.yml / MetricFlow / Mermaid 図は出力時に都度生成。SSoT はオントロジーだけ。コピーが増えない |

---

## 隣接 OSS / 製品との関係

metamesh は競合ではなく、上流の **「業務概念の SSoT」レイヤ** を埋める。

| 製品 | 主たる役割 | metamesh との関係 |
|---|---|---|
| **Open Semantic Interchange (OSI)** | semantic layer の vendor-neutral 交換フォーマット (Snowflake / dbt Labs / Salesforce / Databricks 主導) | OSI v0.1.1 YAML への export 機能 (`generate_osi_yaml` MCP tool) を実装済み。OSI 経由で BI / AI tool に接続可能。bidirectional (import) は v1.0 ロードマップ |
| **dbt Semantic Layer / MetricFlow** | metric 定義と consume API | metamesh のオントロジーから semantic_models / metrics を生成 |
| **OpenMetadata / DataHub / Atlan** | 実装後 catalog (lineage / discovery) | metamesh は SSoT、catalog は使い倒すレイヤ。並存可能 (補完関係) |
| **Cube / GoodData** | semantic layer + caching + API | metamesh は定義の上流、Cube は配信下流 |
| **Protégé / GraphDB / Neo4j n10s** | オントロジー編集 / グラフ DB | metamesh の JSON-LD を直接読める。深い分析はそちらで |
| **GraphRAG (Microsoft / LlamaIndex 等)** | 知識グラフを使った AI 検索 | metamesh のオントロジーを GraphRAG の入力として使える (将来) |

---

## やらないこと (非ゴール)

範囲を明確化するため、以下は意図的に **やらない**:

- **Catalog 機能** (lineage 自動収集、column-level provenance、所有権管理): OpenMetadata / DataHub / Atlan に任せる
- **Semantic layer の query engine 化**: Cube / dbt Semantic Layer に任せる
- **独自 BI フロントエンド**: Protégé / WebVOWL / Tableau / Superset に任せる
- **データ自体の保管**: ドメインデータは外部 (`METAMESH_ONTOLOGY_ROOT` でユーザーが指定)
- **アクセス制御 / governance UI**: data-governance / data-access-control 領域は別ツール

---

## ロードマップ概観

時系列の優先順位は下記:

| フェーズ | 期間 (目安) | 主要アイテム |
|---|---|---|
| 現在 (v0.1) | 完了 | Core MCP (add_concept / add_relationship / query_concept) + 8 Skills + 多 extension 対応 |
| v0.2 | 短期 | OSI (Open Semantic Interchange) export, PyPI 公開 |
| v0.3 | 中期 | Neo4j / LPG export, SHACL validation, `add_metric` |
| v1.0 | 長期 | OSI bidirectional, GraphRAG bridge, conformance test suite |

詳細は [`README.md`](README.md#ロードマップ-フレームワーク本体) のロードマップ表を参照。

---

## ライセンスとコントリビューション

- **License**: Apache-2.0
- **コントリビューション歓迎**: 特に OSI export / Neo4j export / SHACL 周辺
- **参照実装**: [vtuber-analytics](https://github.com/Islanders-Treasure0969/vtuber-analytics)
   (VTuber 配信メタデータをこのフレームワークで構造化)

意見・PR は [Issues](https://github.com/Islanders-Treasure0969/metamesh/issues) へ。
