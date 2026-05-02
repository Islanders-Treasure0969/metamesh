"""metamesh ontology の Holodex API 実データ検証スクリプト。

Holodex (https://holodex.net) は VTuber 配信メタデータを公開している
コミュニティ運営のサービス。本スクリプトはその API
(https://docs.holodex.net/) を利用し、metamesh 側のオントロジーが
宣言する `dv:business_key` フィールドが実データと整合するかを検証する
ためのもの。Holodex への明示的な感謝とリンクを README に記載済み。

VTuber ドメインの各 concept が宣言している `dv:business_key` フィールドが
実際の Holodex API レスポンスに存在するかを、少量のサンプル
(既定: チャンネル 5 件 × 各 10 動画) で確認し、Markdown レポートを書き出す。

Usage:
    # (1) 環境変数で:
    export HOLODEX_API_KEY=<your-key>
    uv run python scripts/validate_holodex.py

    # (2) .env ファイルで (.gitignore 済み):
    cp .env.example .env
    # .env を編集して key を設定
    uv run python scripts/validate_holodex.py

    # (3) 1Password CLI 連携 (推奨、key を平文で保存しない):
    # .env または env var の値を `op://Vault/Item/field` 形式にすると、
    # 起動時に `op read` で取得する。要 `op` CLI と 1Password セッション。
    echo 'HOLODEX_API_KEY=op://Personal/Holodex/credential' > .env

無料 API key は https://holodex.net (Account Settings → API) から取得。

出力: ``output/validation/holodex_coverage.md``
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

API_BASE = "https://holodex.net/api/v2"
REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = REPO_ROOT / "output" / "validation" / "holodex_coverage.md"
ENV_PATH = REPO_ROOT / ".env"
HTTP_TIMEOUT_SEC = 30

# Identifies this client to Holodex's edge. Holodex sits behind Cloudflare,
# whose bot management blocks the default `Python-urllib/*` UA at the edge
# (HTTP 403). A descriptive UA both bypasses the block and is good API
# citizenship.
USER_AGENT = (
    "metamesh-validator/0.1 "
    "(+https://github.com/Islanders-Treasure0969/metamesh)"
)


# ---------------------------------------------------------------------------
# Config (env var or .env file, env var wins)
# ---------------------------------------------------------------------------


def _load_env_file(path: Path) -> dict[str, str]:
    """軽量 .env パーサ。`KEY=value` 形式、`#` コメントと空行は無視。

    値の前後のシングル/ダブルクォートは剥がす。`export` プレフィックスは無視。
    依存ライブラリを増やしたくないので python-dotenv は使わない。
    """
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        out[key.strip()] = value
    return out


def _resolve_op_reference(value: str) -> str:
    """値が ``op://`` で始まる場合、1Password CLI で実体を取得する。

    1Password の `op` CLI が PATH にあり、かつ session が有効である必要が
    ある (locked なら起動時に biometric/password プロンプトが出る)。
    `op` が未インストールなら、ガイダンス付きで明確に終了する。
    """
    if not value.startswith("op://"):
        return value
    op_bin = shutil.which("op")
    if not op_bin:
        raise SystemExit(
            f"Value `{value}` looks like a 1Password reference but the `op` CLI "
            "is not on PATH.\n"
            "Install it (https://developer.1password.com/docs/cli/get-started/) "
            "or replace the value with the actual key."
        )
    try:
        result = subprocess.run(
            [op_bin, "read", value],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise SystemExit(
            f"Failed to read 1Password reference `{value}`:\n"
            f"  stderr: {e.stderr.strip()}\n"
            "Tips: run `op signin` first; verify the reference path matches an "
            "existing item field."
        ) from e
    return result.stdout.strip()


def _resolve_api_key() -> str:
    key = os.environ.get("HOLODEX_API_KEY")
    if not key:
        file_env = _load_env_file(ENV_PATH)
        key = file_env.get("HOLODEX_API_KEY", "")
    if not key:
        raise SystemExit(
            "HOLODEX_API_KEY is not set.\n"
            "Either:\n"
            "  - export HOLODEX_API_KEY=<your-key>\n"
            "  - or copy .env.example to .env and fill it in (supports both "
            "raw values and `op://` references for 1Password CLI)\n"
            "Get a free key at https://holodex.net (Account Settings → API)."
        )
    return _resolve_op_reference(key)


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------


def _http_get_json(url: str, *, api_key: str) -> Any:
    headers = {"X-APIKEY": api_key, "User-Agent": USER_AGENT}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SEC) as resp:
        return json.loads(resp.read())


def fetch_channels(api_key: str, *, org: str, limit: int) -> list[dict[str, Any]]:
    qs = urllib.parse.urlencode({"org": org, "limit": limit, "type": "vtuber"})
    return _http_get_json(f"{API_BASE}/channels?{qs}", api_key=api_key)


def fetch_videos_for_channel(
    api_key: str, *, channel_id: str, limit: int
) -> list[dict[str, Any]]:
    qs = urllib.parse.urlencode({"limit": limit, "include": "mentions"})
    return _http_get_json(
        f"{API_BASE}/channels/{channel_id}/videos?{qs}",
        api_key=api_key,
    )


# ---------------------------------------------------------------------------
# Validation logic
# ---------------------------------------------------------------------------


def validate_field(
    *,
    name: str,
    records: list[dict[str, Any]],
    field: str,
    format_hint: str = "",
    optional: bool = False,
) -> dict[str, str]:
    if not records:
        return {"name": name, "status": "⚠️ skipped", "detail": "no records"}
    present = [r for r in records if r.get(field) not in (None, "")]
    pct = 100.0 * len(present) / len(records)
    if pct == 100.0:
        status = "✅ ok"
    elif optional:
        status = "ℹ️ partial (field is optional)"
    elif pct >= 50:
        status = "⚠️ partial"
    else:
        status = "❌ mostly missing"
    parts = [f"{len(present)}/{len(records)} have non-empty `{field}` ({pct:.0f}%)"]
    if format_hint:
        parts.append(f"expected: {format_hint}")
    if present:
        sample = json.dumps(present[0].get(field), ensure_ascii=False)
        parts.append(f"sample: `{sample}`")
    return {"name": name, "status": status, "detail": " — ".join(parts)}


def run_validations(
    channels: list[dict], videos: list[dict]
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []

    findings.append(
        validate_field(
            name="Channel.business_key (channel.id)",
            records=channels,
            field="id",
            format_hint="UCxxxx (YouTube channel ID)",
        )
    )
    findings.append(
        validate_field(
            name="Organization.business_key (channel.org)",
            records=channels,
            field="org",
            format_hint="org name like 'Hololive', 'Nijisanji'",
        )
    )
    findings.append(
        validate_field(
            name="Stream.business_key (video.id)",
            records=videos,
            field="id",
            format_hint="YouTube video ID",
        )
    )
    findings.append(
        validate_field(
            name="Topic.business_key (video.topic_id)",
            records=videos,
            field="topic_id",
            format_hint="e.g. 'singing', 'minecraft' (often null in raw API)",
            optional=True,
        )
    )

    clips = [v for v in videos if v.get("type") == "clip"]
    findings.append(
        {
            "name": "Clip.business_key (video.id where type='clip')",
            "status": "✅ ok" if clips else "ℹ️ none in sample",
            "detail": (
                f"{len(clips)}/{len(videos)} videos have type='clip' "
                "(channel-owned uploads sample, so clips are sparse here; "
                "use /api/v2/videos?type=clip for clip-focused validation)"
            ),
        }
    )

    with_mentions = [v for v in videos if v.get("mentions")]
    findings.append(
        {
            "name": "Collaboration / participates_in (via video.mentions[])",
            "status": "✅ ok" if with_mentions else "ℹ️ none in sample",
            "detail": (
                f"{len(with_mentions)}/{len(videos)} videos carry non-empty "
                "`mentions[]` (collab participants other than the channel owner)"
            ),
        }
    )

    findings.append(
        {
            "name": "Streamer.business_key (provisional: main channel.id)",
            "status": "⚠️ provisional",
            "detail": (
                "Holodex has no streamer-level identifier; the ontology uses "
                "the main channel.id as Streamer's business key. Recorded in "
                "`ontology/concepts/Streamer.jsonld` under "
                "`dv:business_key_strategy`."
            ),
        }
    )

    return findings


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def render_report(
    findings: list[dict[str, str]],
    *,
    org: str,
    n_channels: int,
    n_videos: int,
) -> str:
    lines = [
        "# metamesh ontology — Holodex API 検証レポート",
        "",
        "データソース: [Holodex](https://holodex.net) "
        "([API ドキュメント](https://docs.holodex.net/))。"
        "本レポートは Holodex API レスポンスのスキーマ整合性を確認する目的で、"
        "ごく少量のサンプルメタデータを掲載している。",
        "",
        f"サンプル: **{n_channels} channels** (org=`{org}`, type=`vtuber`), "
        f"**{n_videos} videos** total。",
        "",
        "各行は metamesh concept が宣言する `dv:business_key` フィールドが、"
        "実際の Holodex API レスポンスに存在するかを確認している。",
        "",
        "| Concept | Status | Detail |",
        "|---|---|---|",
    ]
    for f in findings:
        lines.append(f"| {f['name']} | {f['status']} | {f['detail']} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "_再生成: `uv run python scripts/validate_holodex.py` "
        "(要 `HOLODEX_API_KEY` 環境変数 or `.env`)_"
    )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _positive_int_setting(raw: str, *, name: str) -> int:
    """設定値を正の整数として解釈する。失敗時はトレースバックではなく
    `SystemExit` で短く分かりやすく終わる。"""
    try:
        value = int(raw)
    except ValueError as e:
        raise SystemExit(
            f"{name}=`{raw}` is not a valid integer. "
            "Set it to a positive integer (e.g. 5) or unset to use the default."
        ) from e
    if value <= 0:
        raise SystemExit(
            f"{name}=`{raw}` must be a positive integer (got {value})."
        )
    return value


def main() -> int:
    api_key = _resolve_api_key()
    file_env = _load_env_file(ENV_PATH)

    def cfg(key: str, default: str) -> str:
        return os.environ.get(key) or file_env.get(key) or default

    org = cfg("HOLODEX_VALIDATE_ORG", "Hololive")
    n_channels = _positive_int_setting(
        cfg("HOLODEX_VALIDATE_CHANNELS", "5"),
        name="HOLODEX_VALIDATE_CHANNELS",
    )
    n_videos_per_channel = _positive_int_setting(
        cfg("HOLODEX_VALIDATE_VIDEOS", "10"),
        name="HOLODEX_VALIDATE_VIDEOS",
    )

    print(f"Fetching {n_channels} channels (org={org}, type=vtuber)...", file=sys.stderr)
    channels = fetch_channels(api_key, org=org, limit=n_channels)
    print(f"  → {len(channels)} channels received", file=sys.stderr)

    all_videos: list[dict[str, Any]] = []
    for ch in channels:
        ch_id = ch.get("id")
        ch_name = ch.get("name") or ch.get("english_name") or ch_id or "?"
        if not ch_id:
            continue
        print(f"  Fetching videos for {ch_name} ({ch_id})...", file=sys.stderr)
        try:
            videos = fetch_videos_for_channel(
                api_key, channel_id=ch_id, limit=n_videos_per_channel
            )
        except Exception as e:  # noqa: BLE001 — we want to surface and continue
            print(f"    ! failed: {e}", file=sys.stderr)
            continue
        all_videos.extend(videos)
    print(f"  → {len(all_videos)} videos collected total", file=sys.stderr)

    findings = run_validations(channels, all_videos)
    report = render_report(
        findings,
        org=org,
        n_channels=len(channels),
        n_videos=len(all_videos),
    )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"\n✓ Report: {REPORT_PATH.relative_to(REPO_ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
