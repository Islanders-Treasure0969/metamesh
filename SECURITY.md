# Security Policy

metamesh のセキュリティ脆弱性を発見した方への報告ガイド。

## サポート対象バージョン

公開バージョンは小さいので、現状は **最新の `main` ブランチのみ** がセキュリティ更新の対象。

| バージョン | サポート状況 |
|---|---|
| `main` (latest) | ✅ アクティブにメンテナンス |
| 過去の tag (v0.x) | ❌ 個別メンテナンスは行わない |

PyPI 公開後は、最新マイナーリリースのみサポート対象に切り替える予定 (詳細は [Issue #29](https://github.com/Islanders-Treasure0969/metamesh/issues/29) 解決時に更新)。

## 脆弱性の報告方法

**公開 Issue / PR / Discussion で脆弱性内容を投稿しないでください。** 修正前に詳細が公開されると、悪用のリスクが高まります。

### 推奨経路: GitHub Private Vulnerability Reporting (PVR)

1. リポジトリの [Security タブ](https://github.com/Islanders-Treasure0969/metamesh/security) を開く
2. "Report a vulnerability" を選択
3. 詳細を入力して送信

PVR は GitHub が提供する non-public な報告経路で、メンテナのみが内容を閲覧できます。

### 代替経路: メール

PVR が利用できない場合は、リポジトリ所有者の GitHub プロフィールに記載のメールアドレス宛に報告してください。件名には `[metamesh security]` を含めてください。

## 報告に含めて欲しい内容

迅速な対応のため、可能な範囲で以下の情報を含めてください:

- **影響範囲**: どの component (MCP server / SPARQL query / extension parser / 等) に影響するか
- **再現手順**: 最小限のコード or オントロジー入力で再現できる手順
- **攻撃シナリオ**: 想定される悪用方法
- **影響度の見積もり**: 情報漏洩 / 任意コード実行 / DoS / etc.
- **環境情報**: Python バージョン、OS、metamesh バージョン (commit SHA)

## 対応タイムライン目安

個人 OSS のため、商用製品レベルの SLA は提供できません。ベストエフォートでの対応:

| ステップ | 目安 |
|---|---|
| 初回応答 | 報告から 7 日以内 |
| 影響範囲の確定 | 14 日以内 |
| 修正 PR 作成 | Critical: 30 日以内 / High: 60 日以内 / Medium 以下: 90 日以内 |
| 公開 (CVE / advisory 発行) | 修正 PR merge 後すみやかに |

## 既知の信頼境界 (Threat Model 概略)

metamesh は以下を **信頼する** 前提で設計されています:

- ✅ `METAMESH_ONTOLOGY_ROOT` が指すディレクトリの内容 (ユーザー自身が書いたファイル)
- ✅ Claude Desktop / Code 経由で渡される MCP リクエスト (ローカルプロセス間通信)
- ✅ ローカルファイルシステムの read/write 権限

逆に以下は **信頼しません**:

- ❌ 任意 SPARQL クエリ → `query_concept` で `INSERT/DELETE/DROP/LOAD` 等の Update 系操作はブロック (read-only 契約、PR #24 で実装)
- ❌ 任意 JSON-LD 入力 → rdflib の parse セキュリティ機能に依拠
- ❌ 外部ネットワーク → metamesh 自体は外部 API を呼び出さない (ユーザーが書く Skill が呼び出す可能性はある)

## 守られている既存の対策

- **Secret scanning**: GitHub Native + [gitleaks-action](https://github.com/gitleaks/gitleaks-action) で全 commit history を CI で検査
- **SPARQL Update 防止**: `query_concept` での書き込み系操作をブロック ([src/metamesh/queries/concept.py](src/metamesh/queries/concept.py))
- **依存関係の更新**: Dependabot で pip / GitHub Actions を週次更新
- **Static analysis**: CodeQL workflow で Python コードの脆弱性パターンを CI で検出
- **CI workflow 権限最小化**: 全 workflow で `permissions: read-all` を default、書き込みが必要な場合のみ明示

## 謝辞

責任ある開示 (Coordinated Disclosure) に従って報告してくださった方には、このセクションでお名前 (希望者のみ) と修正 PR / advisory への謝辞リンクを記載します。
