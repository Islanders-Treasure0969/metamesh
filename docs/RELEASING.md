# リリース手順

metamesh の PyPI / TestPyPI への release 手順。`.github/workflows/release.yml` が自動化を担う。

## 前提: Trusted Publishers のセットアップ (初回のみ)

長期 token を repo secret に置かない設計 (PyPI Trusted Publishers / OIDC)。
**最初の release 前に、PyPI と TestPyPI の両方で Trusted Publisher を登録する必要がある**。

### 1. PyPI 側

[https://pypi.org/manage/account/publishing/](https://pypi.org/manage/account/publishing/) で **Add a new pending publisher**:

| 項目 | 値 |
|---|---|
| PyPI Project Name | `metamesh` |
| Owner | `Islanders-Treasure0969` |
| Repository name | `metamesh` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

### 2. TestPyPI 側

[https://test.pypi.org/manage/account/publishing/](https://test.pypi.org/manage/account/publishing/) で同じく Add a new pending publisher:

| 項目 | 値 |
|---|---|
| PyPI Project Name | `metamesh` |
| Owner | `Islanders-Treasure0969` |
| Repository name | `metamesh` |
| Workflow name | `release.yml` |
| Environment name | `testpypi` |

### 3. GitHub 側 Environments

[https://github.com/Islanders-Treasure0969/metamesh/settings/environments](https://github.com/Islanders-Treasure0969/metamesh/settings/environments) で 2 つ作成:

- **`pypi`**: 推奨設定
  - **Required reviewers**: 自分自身を追加 (誤 publish 防止のため手動 approval を強制)
  - **Deployment branches and tags**: `Selected branches and tags` → `v*.*.*` パターン (tag 経由のみ許可)
- **`testpypi`**: 推奨設定
  - Required reviewers: なし (dry-run なので即実行可)
  - Deployment branches: 制限なし

---

## 通常リリース手順

### ステップ 1: TestPyPI で dry-run

リリース前に必ず TestPyPI で動作確認する。

1. [Actions タブ → Release workflow](https://github.com/Islanders-Treasure0969/metamesh/actions/workflows/release.yml) を開く
2. **"Run workflow"** ボタン → branch: `main` → target: `testpypi` → Run
3. workflow が完了したら、別環境で install 確認:

   ```bash
   pip install -i https://test.pypi.org/simple/ \
       --extra-index-url https://pypi.org/simple/ \
       metamesh
   metamesh --help  # またはオントロジー設定して MCP server 起動確認
   ```

   `--extra-index-url https://pypi.org/simple/` は、本依存 (mcp / rdflib / pyld / pyyaml) を本番 PyPI から取るためのおまじない。

### ステップ 2: バージョン番号を bump

```bash
# pyproject.toml の version を編集 (例: 0.1.0 → 0.2.0)
# semver: MAJOR.MINOR.PATCH
#   MAJOR: 後方互換破壊
#   MINOR: 後方互換ある機能追加
#   PATCH: bug fix のみ

git checkout -b release/v0.2.0
# pyproject.toml 編集
git commit -am "Bump version to v0.2.0"
git push -u origin release/v0.2.0
```

PR を出して merge。

### ステップ 3: tag 打ちと PyPI publish

main に merge 済みの commit に tag を打つ:

```bash
git checkout main
git pull
git tag -s v0.2.0 -m "Release v0.2.0"  # GPG signed tag (推奨)
# GPG なしなら:
# git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
```

tag push が trigger となり、`release.yml` が:

1. **build** job: `uv build` → sdist + wheel 生成、`twine check` で検証
2. **publish-pypi** job: `pypi` environment (Required reviewers approval 待ち) → 承認後 PyPI に OIDC で publish
3. **github-release** job: GitHub Releases に release notes 自動生成 + artifact 添付

### ステップ 4: 確認

```bash
# PyPI にアップ完了したか
curl -s https://pypi.org/pypi/metamesh/json | jq '.info.version'

# 別環境 (Docker など) でクリーン install
pip install metamesh==0.2.0
metamesh --help
```

---

## トラブルシューティング

### `twine check` が fail する

- README.md / 長い description が PyPI の RST/Markdown レンダラで読めない場合に発生
- `uv build` 後の `dist/*.whl` を `unzip -p dist/metamesh-*.whl '*.dist-info/METADATA'` で確認

### `id-token: write` permission denied

- Environment が正しく設定されてない (Trusted Publisher 登録 + GitHub environment が一致してない)
- 上記「前提: Trusted Publishers のセットアップ」を再確認

### Required reviewer approval が来ない

- `pypi` environment の Required reviewers に自分が追加されてるか確認
- Actions タブの workflow run → Reviewers で approval

### tag push したのに workflow が走らない

- `.github/workflows/release.yml` の `on.push.tags` パターン (`v*.*.*`) と tag 名の整合確認
- `v0.2.0` ✓ / `0.2.0` (v なし) ✗ / `v0.2` (patch なし) ✗

### TestPyPI で metamesh の依存が解決できない

- `mcp` などの依存が TestPyPI に存在しない場合に発生
- 解決: `pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ metamesh` (本番 PyPI を fallback に)

---

## yank / 削除手順

リリース後に致命的なバグが見つかった場合:

```bash
# yank (バージョンを installable から外す。完全削除ではない)
# PyPI Web UI: https://pypi.org/manage/project/metamesh/release/0.2.0/
# → "Options" → "Yank release"
```

**完全削除 (delete) は基本的にやらない**。yank で「使うな」を表明し、修正版 (例 v0.2.1) を出すのが PyPI 慣習。
