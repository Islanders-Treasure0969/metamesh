# 参考資料ポインタ

本リポジトリは設計判断の根拠となる外部資料を **コピーせずに参照する**。
原典の更新を取りこぼさないため、必要なときに該当パスを `Read` で開くこと。

## ローカル原典 (`/Users/iwashita/practical_data_vault/`)

### 設計の出発点 (必読)

| ファイル | 内容 | 関連する metamesh 機能 |
|---|---|---|
| `chapter_12_design_process.md` | モデルストーミング全体プロセス | `add_concept` のインタビュー設計 |
| `chapter_12_detail_cbc_nbr_process.md` | CBC/NBR フォームの詳細 | インタビュー質問項目の根拠 |
| `chapter_13_ontology_taxonomy.md` | DV と オントロジーの接続論 | 拡張名前空間 `dv:` の設計 |
| `research_part3_framework.md` | Ontology-Driven Metadata Pipeline | プロジェクト全体の理論 |

### 周辺 (必要に応じて)

| ファイル | 内容 |
|---|---|
| `research_part1_problem.md` | メタデータの 5 つの断絶 (問題提起) |
| `research_part2_current_state.md` | 既存技術の整理 |
| `research_part4_5_implementation_research.md` | 実装調査 |
| `chapter_06_raw_vault.md` / `chapter_07_business_vault.md` / `chapter_08_information_mart.md` | DV の各層 (Step 2 以降の `generate_dbt_yaml` で参照) |
| `chapter_03_extended_concepts.md` | DV 拡張概念 (Multi-Active Sat 等) |
| `appendix_d_essences.md` / `appendix_e_common_mistakes.md` | DV のエッセンスと典型的な失敗例 |

## プロジェクト権威ドキュメント

`docs/PROJECT_CONTEXT.md` — Claude.ai での議論を引き継ぐためのコンテキスト。
原典は `/Users/iwashita/metadata_oss/PROJECT_CONTEXT.md`。
変更があったときは本リポジトリ側にも反映する。
