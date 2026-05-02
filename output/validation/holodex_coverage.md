# metamesh ontology — Holodex API 検証レポート

データソース: [Holodex](https://holodex.net) ([API ドキュメント](https://docs.holodex.net/))。本レポートは Holodex API レスポンスのスキーマ整合性を確認する目的で、ごく少量のサンプルメタデータを掲載している。

サンプル: **5 channels** (org=`Hololive`, type=`vtuber`), **50 videos** total。

各行は metamesh concept が宣言する `dv:business_key` フィールドが、実際の Holodex API レスポンスに存在するかを確認している。

| Concept | Status | Detail |
|---|---|---|
| Channel.business_key (channel.id) | ✅ ok | 5/5 have non-empty `id` (100%) — expected: UCxxxx (YouTube channel ID) — sample: `"UC060r4zABV18vcahAWR1n7w"` |
| Organization.business_key (channel.org) | ✅ ok | 5/5 have non-empty `org` (100%) — expected: org name like 'Hololive', 'Nijisanji' — sample: `"Hololive"` |
| Stream.business_key (video.id) | ✅ ok | 50/50 have non-empty `id` (100%) — expected: YouTube video ID — sample: `"SA9lhXmi5tY"` |
| Topic.business_key (video.topic_id) | ℹ️ partial (field is optional) | 48/50 have non-empty `topic_id` (96%) — expected: e.g. 'singing', 'minecraft' (often null in raw API) — sample: `"FreeChat"` |
| Clip.business_key (video.id where type='clip') | ℹ️ none in sample | 0/50 videos have type='clip' (channel-owned uploads sample, so clips are sparse here; use /api/v2/videos?type=clip for clip-focused validation) |
| Collaboration / participates_in (via video.mentions[]) | ✅ ok | 10/50 videos carry non-empty `mentions[]` (collab participants other than the channel owner) |
| Streamer.business_key (provisional: main channel.id) | ⚠️ provisional | Holodex has no streamer-level identifier; the ontology uses the main channel.id as Streamer's business key. Recorded in `ontology/concepts/Streamer.jsonld` under `dv:business_key_strategy`. |

---

_再生成: `uv run python scripts/validate_holodex.py` (要 `HOLODEX_API_KEY` 環境変数 or `.env`)_
