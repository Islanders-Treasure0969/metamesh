# Contributing to metamesh

metamesh は個人開発の OSS。コントリビューション歓迎。このドキュメントは「どこに何を投稿すれば届くか」の入口。

## 報告先の早見表

| やりたいこと | 行き先 |
|---|---|
| **セキュリティ脆弱性の報告** | **公開せず** [GitHub Private Vulnerability Reporting](https://github.com/Islanders-Treasure0969/metamesh/security/advisories/new) で送る ([SECURITY.md](SECURITY.md) 参照) |
| バグ報告 | [Issues](https://github.com/Islanders-Treasure0969/metamesh/issues) で `bug` ラベル |
| 機能要望 | [Issues](https://github.com/Islanders-Treasure0969/metamesh/issues) で `enhancement` ラベル |
| 質問・議論 | [Discussions](https://github.com/Islanders-Treasure0969/metamesh/discussions) (admin が enable した場合) もしくは Issue |
| Skill / ドキュメントの改善提案 | Issue or PR どちらでも |

**重要**: セキュリティ脆弱性を public Issue / PR / Discussion に書かないでください。詳細は [SECURITY.md](SECURITY.md)。

## 開発環境セットアップ

### 必須

- Python 3.11 以上
- [uv](https://docs.astral.sh/uv/) (Python パッケージ管理)
- git

### 初回セットアップ

```bash
git clone https://github.com/Islanders-Treasure0969/metamesh.git
cd metamesh
uv sync --extra dev          # 依存をインストール
uv run pre-commit install    # pre-commit hook を有効化 (推奨)
uv run pytest -v             # 動作確認 (現状 69 tests)
```

`pre-commit install` を実行すると、以後 `git commit` 前に gitleaks / ruff / 各種チェックが local で走る。

### よく使うコマンド

```bash
uv run pytest -v             # テスト
uv run ruff check .          # lint
uv run ruff format .         # format
uv run pre-commit run --all-files   # 全ファイルに pre-commit を適用
```

## ブランチ戦略 / PR フロー

1. `main` から feature ブランチを切る (例: `feat/add-metric` / `docs/positioning-update` / `security/harden-X`)
2. commit メッセージは `<Verb> <noun phrase>` の英語タイトル + 日本語本文 (本リポジトリの慣例)
3. push して PR を作成
4. CodeRabbit が自動レビューを行う。指摘に対応するか反論
5. 自分でも内容確認した上で merge (linear history を保つため squash or rebase)

### コミットメッセージの例

タイトル: 短い動詞句、英語、~50 文字以内
```
Add SHACL validation for ontology integrity
Fix HTTP 403 from Holodex API (set User-Agent header)
Translate remaining English prose in cbc / nbr Skills
```

本文: 必要に応じて日本語で詳細記述。

末尾に Co-Authored-By を入れる慣例:
```
Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

## CI で走るチェック

PR を出すと以下が自動実行される:

| Workflow | 内容 |
|---|---|
| `Tests` | pytest (Python 3.11 / 3.12) + ruff |
| `gitleaks` | 全 history に対する secret scan |
| `CodeQL` | Python SAST (Static Application Security Testing) |
| `Dependabot` | 依存関係の脆弱性アラート (週次) |

すべて green でないと merge できない (branch protection 設定による)。

## コードスタイル

- **言語**: Python (server / queries / ontology / ext) + Markdown (Skills / docs)
- **lint**: ruff (line-length 100, target Python 3.11)
- **コメント**: `# WHY:` を残す。`# WHAT:` (コードを再述する) は避ける
- **言語選択 (Markdown)**:
  - **README / docs / SKILL.md / コミットメッセージ本文 / Issue / PR description**: 日本語が default
  - **コミットメッセージタイトル**: 英語 (一文の動詞句)
  - **コードコメント**: 状況に応じて (Python は英語が一般的)

## オントロジー / Skill の追加

新しい Skill を追加する場合:

1. `.claude/skills/<skill-name>/SKILL.md` に `name`, `description`, frontmatter を書く
2. workflow / template をサブディレクトリに置く (例: `.claude/skills/dv-implementation-design/templates/`)
3. README ロードマップにエントリ追加
4. 必要なら関連 Issue を起票・割り当て

## ライセンス

contribution は Apache-2.0 ライセンスで取り込まれます。PR を送る = このライセンス条件で contribution することに同意した、と見なされます。

## 連絡

- 質問: [Issues](https://github.com/Islanders-Treasure0969/metamesh/issues) (Discussion が enable されてればそちら)
- セキュリティ: [SECURITY.md](SECURITY.md)
- 緊急: リポジトリ所有者の GitHub プロフィール記載のメール
