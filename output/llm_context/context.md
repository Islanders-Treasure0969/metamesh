# VTuber Domain Ontology

_Generated from `ontology` — 7 concepts, 6 relationships._

## Concepts

| ID | Label (ja) | Label (en) | DV |
|---|---|---|---|
| `Channel` | チャンネル | Channel | HUB_CHANNEL |
| `Clip` | 切り抜き | Clip | HUB_CLIP |
| `Collaboration` | コラボ | Collaboration |  |
| `Organization` | 事務所 | Organization | HUB_ORGANIZATION |
| `Stream` | 配信 | Stream | HUB_STREAM |
| `Streamer` | 配信者 | Streamer | HUB_STREAMER |
| `Topic` | トピック | Topic | HUB_TOPIC |

### `Channel` — チャンネル / Channel

YouTube・Twitch 等のプラットフォーム上で開設された、配信者が所有する個別の配信枠。1 人の Streamer がメインチャンネルに加え、歌枠・ゲーム実況・アーカイブ等の用途別サブチャンネルを複数所有することがある。Holodex API の channel エンティティに対応。

_An individual streaming slot on a platform (YouTube/Twitch) owned by a streamer. A Streamer may own multiple Channels: a main channel plus sub-channels for songs, gameplay, archives, etc. Corresponds to the Holodex API channel entity._

**Synonyms:**
- ja: YouTubeチャンネル, サブチャンネル, 歌チャンネル
- en: YouTube Channel, Sub-channel

**Ontology links:**
- related: `Streamer`, `Stream`, `Organization`

**DV implementation:**
- `hub`: HUB_CHANNEL
- `business_key`: channel_id
- `business_key_source`: Holodex channel.id (= YouTube UCxxxx)
- `owned_by`: Streamer (N:1, via LNK_STREAMER_CHANNEL)
- `channel_role_attribute`: main | song | gaming | archive | other

_Scheme: `VTuberDomain`_

### `Clip` — 切り抜き / Clip

元の配信 (Stream) の一部を切り出して編集された二次的な動画コンテンツ。切り抜き師 (clipper) と呼ばれる第三者が制作することが多い。元配信との派生関係を持ち、Holodex API では type='clip' として識別される。

_A secondary video derived from a portion of an original Stream, often produced by a third party known as a clipper. Maintains a derivation relationship to the source Stream. Identified as type='clip' in the Holodex API._

**Synonyms:**
- ja: 切り抜き動画, クリップ
- en: Clip Video, Highlight

**Ontology links:**
- related: `Stream`, `Streamer`

**DV implementation:**
- `hub`: HUB_CLIP
- `business_key`: clip_video_id
- `business_key_source`: Holodex video.id where type='clip'
- `derived_from`: Stream (N:1, via LNK_CLIP_STREAM)

_Scheme: `VTuberDomain`_

### `Collaboration` — コラボ / Collaboration

複数の配信者が 1 つの配信に同時出演する関係性イベント。Holodex API では video.mentions[] フィールドで関連付けられる。配信主 (owner) と出演者 (mentions) の役割を区別する。技術的な実装 (DV Link) の記述は participates_in 関係性側に集約してある。

_A relationship event in which multiple streamers appear together in a single stream. Surfaced via the video.mentions[] field on the Holodex API. The owner (broadcaster) role is distinguished from the guest (mentions) role. Technical implementation metadata (DV link) is kept on the participates_in relationship._

**Synonyms:**
- ja: コラボ配信, 合同配信, ゲスト出演
- en: Collab, Joint Stream, Guest Appearance

**Ontology links:**
- related: `Streamer`, `Stream`

_Scheme: `VTuberDomain`_

### `Organization` — 事務所 / Organization

配信者が所属する VTuber 事務所・グループ。ホロライブ・にじさんじ・ぶいすぽっ! 等が該当。所属配信者にブランド・サポート・運営機能を提供する。個人勢の場合はいずれの Organization にも所属しない。

_A VTuber agency or group that streamers belong to (e.g., Hololive, Nijisanji, VSPO!). Provides brand, operational support, and management to its members. Independent streamers do not belong to any Organization._

**Synonyms:**
- ja: プロダクション, グループ, 事務所, ホロプロ, ライバー事務所
- en: Agency, Production, Group

**Ontology links:**
- related: `Streamer`

**DV implementation:**
- `hub`: HUB_ORGANIZATION
- `business_key`: org_name
- `business_key_source`: Holodex channel.org (e.g., 'Hololive', 'Nijisanji', 'Independents')

_Scheme: `VTuberDomain`_

### `Stream` — 配信 / Stream

Channel 上で行われる 1 回の配信イベント。ライブ配信・プレミア公開・アーカイブ動画を 1 単位として扱う。Holodex API の video エンティティ (type='stream') に対応。各 Stream は必ず 1 つの Channel に所属する。

_A single streaming event that takes place on a Channel. Live broadcasts, premieres, and archived videos are all treated as one unit. Corresponds to the Holodex API video entity (type='stream'). Each Stream belongs to exactly one Channel._

**Synonyms:**
- ja: 放送, ライブ配信, 動画
- en: Broadcast, Live, Video

**Ontology links:**
- related: `Channel`, `Streamer`, `Collaboration`, `Clip`, `Topic`

**DV implementation:**
- `hub`: HUB_STREAM
- `business_key`: video_id
- `business_key_source`: Holodex video.id (= YouTube video ID)
- `belongs_to`: Channel (N:1, via LNK_STREAM_CHANNEL)

_Scheme: `VTuberDomain`_

### `Streamer` — 配信者 / Streamer

バーチャルアバターを用いて配信活動を行うキャラクター単位のエンティティ。中の人ではなく、視聴者から認識される配信キャラクターを 1 単位として扱う (中の人交代があっても同一 Streamer)。1 人の Streamer は複数の Channel (メイン + サブチャンネル) を所有しうる。事務所所属・個人勢の双方を含む。

_A character-level entity that conducts streaming activities using a virtual avatar. The unit of identity is the recognized character (not the performer behind it); the same Streamer persists even if the inside performer changes. A single Streamer may own multiple Channels (main + sub). Includes both agency-affiliated talents and independent streamers._

**Synonyms:**
- ja: VTuber, ライバー, バーチャルライバー, タレント
- en: VTuber, Virtual Streamer, Talent

**Ontology links:**
- related: `Channel`, `Organization`, `Collaboration`, `Stream`

**DV implementation:**
- `hub`: HUB_STREAMER
- `business_key`: streamer_id
- `business_key_strategy`: 暫定対応としてメインチャンネルの channel_id を流用して識別。将来的に streamer-level ID 体系 (org + character_name のハッシュ等) へ移行可能
- `owns`: Channel (1:N)
- `belongs_to`: Organization (N:1, optional)

_Scheme: `VTuberDomain`_

### `Topic` — トピック / Topic

配信のジャンル・テーマを示す分類タグ。ゲーム実況・歌・雑談・ASMR 等。Holodex API の topic_id に対応する分類体系で、1 配信に複数の Topic が紐づく場合がある。

_A classification tag representing the genre or theme of a stream (gaming, music, talk, ASMR, etc.). Maps to the Holodex API topic_id taxonomy. A single Stream may be tagged with multiple Topics._

**Synonyms:**
- ja: ジャンル, カテゴリ, 配信ジャンル
- en: Genre, Category, Tag

**Ontology links:**
- related: `Stream`

**DV implementation:**
- `hub`: HUB_TOPIC
- `business_key`: topic_id
- `business_key_source`: Holodex video.topic_id (e.g., 'singing', 'minecraft')

_Scheme: `VTuberDomain`_

## Relationships

| ID | Label (ja) | Domain | Range | Cardinality | DV Link |
|---|---|---|---|---|---|
| `belongs_to_org` | 事務所に所属する | `Streamer` | `Organization` | N:1 | LNK_STREAMER_ORG |
| `categorized_as` | カテゴリに分類される | `Stream` | `Topic` | N:M | LNK_STREAM_TOPIC |
| `derived_from` | から派生する | `Clip` | `Stream` | N:1 | LNK_CLIP_STREAM |
| `hosts_stream` | 配信をホストする | `Channel` | `Stream` | 1:N | LNK_STREAM_CHANNEL |
| `owns_channel` | チャンネルを所有する | `Streamer` | `Channel` | 1:N | LNK_STREAMER_CHANNEL |
| `participates_in` | 配信に出演する | `Streamer` | `Stream` | N:M | LNK_COLLAB |

### `belongs_to_org` — 事務所に所属する / belongs to organization

`Streamer` → `Organization`  (N:1)

配信者が VTuber 事務所に所属する関係。個人勢の場合は所属しない (関係なし)。Holodex channel.org 由来。

_A streamer is affiliated with a VTuber agency. Independent streamers have no such relationship. Sourced from Holodex channel.org._

**DV implementation:**
- `link`: LNK_STREAMER_ORG
- `cardinality`: N:1
- `optional`: True

_Scheme: `VTuberDomain`_

### `categorized_as` — カテゴリに分類される / categorized as

`Stream` → `Topic`  (N:M)

配信がジャンル/テーマに分類される関係。1 配信に複数の Topic が紐づくことがある。Holodex video.topic_id 由来。

_A stream is classified by genre/theme. A single stream may carry multiple topics. Sourced from Holodex video.topic_id._

**DV implementation:**
- `link`: LNK_STREAM_TOPIC
- `cardinality`: N:M

_Scheme: `VTuberDomain`_

### `derived_from` — から派生する / derived from

`Clip` → `Stream`  (N:1)

切り抜きが元の配信から派生する関係。Holodex API では type='clip' の動画が type='stream' の動画を参照する形で表現される。

_A clip is derived from an original stream. In the Holodex API, videos with type='clip' reference videos with type='stream'._

**DV implementation:**
- `link`: LNK_CLIP_STREAM
- `cardinality`: N:1

_Scheme: `VTuberDomain`_

### `hosts_stream` — 配信をホストする / hosts stream

`Channel` → `Stream`  (1:N)

チャンネル上で 1 回の配信イベントが行われる関係。各 Stream は必ず 1 つの Channel に所属する。Holodex video.channel_id 由来。

_A streaming event takes place on a channel. Each Stream belongs to exactly one Channel. Sourced from Holodex video.channel_id._

**DV implementation:**
- `link`: LNK_STREAM_CHANNEL
- `cardinality`: 1:N

_Scheme: `VTuberDomain`_

### `owns_channel` — チャンネルを所有する / owns channel

`Streamer` → `Channel`  (1:N)

配信者が YouTube/Twitch 等の配信枠を所有する関係。1 人の配信者がメインチャンネルとサブチャンネル (歌・ゲーム実況・アーカイブ等) を複数所有しうる。

_A streamer owns a streaming slot on YouTube/Twitch, etc. A single streamer may own a main channel plus multiple sub-channels (songs, gameplay, archives)._

**DV implementation:**
- `link`: LNK_STREAMER_CHANNEL
- `cardinality`: 1:N
- `role_attribute`: channel_role (main | song | gaming | archive | other)

_Scheme: `VTuberDomain`_

### `participates_in` — 配信に出演する / participates in

`Streamer` → `Stream`  (N:M)

配信者が配信に出演する関係 (コラボを含む)。配信主 (owner) も出演者の 1 人として扱う。Holodex video.mentions[] および video.channel 由来。

_A streamer appears in a stream (including collaborations). The broadcaster (owner) is also treated as a participant. Sourced from Holodex video.mentions[] and video.channel._

**DV implementation:**
- `link`: LNK_COLLAB
- `cardinality`: N:M
- `participants`: HUB_STREAMER, HUB_STREAM
- `business_key_source`: Holodex video.mentions[] + video.channel
- `role_attribute`: participant_role (owner | guest)

_Scheme: `VTuberDomain`_
