---
name: music-toolkit
description: |
  ## 核心功能分区

  ### 📊 数据监控模块（playlist-detail / music-detail）
  **当用户需要获取歌曲或歌单的数据时使用。** 包括：
  - 查看一个歌单里有哪些歌、每首歌的收藏/评论/分享数、发布日期
  - 获取某首歌的统计数据（收藏、评论、分享、播放）
  - 抓取歌单或歌曲数据后推送到飞书群卡片
  - 批量抓取多首歌曲详情
  - **不需要 go-music-dl 后端，不需要 LLM 调用，一条命令直接返回数据**

  支持平台: 汽水音乐（全量数据）、网易云（含评论数）、QQ音乐（基础信息）、酷狗（前10首）

  ### 🎵 下载模块（download / download-playlist / parse-url）
  **当用户需要下载音乐文件时使用。** 包括：
  - 下载单首歌曲 mp3/flac
  - 批量下载整个歌单（自动换源）
  - 解析分享链接并下载
  - 需要 go-music-dl Docker 后端（localhost:8080）

  ### 📤 推送模块（push-* / send-to-chat）
  **当用户需要把音乐数据或文件发送到飞书时使用。**
  - 依赖 feishu-toolkit（../feishu-toolkit/feishu_toolkit.py）
  - 不要使用官方 Feishu MCP 替代

  ⚠️ **模块边界**：数据监控（playlist-detail）和下载（download-playlist）是独立的两件事。
  用户说"看看这个歌单的数据"→ playlist-detail；用户说"下载这个歌单"→ download-playlist。

  ⚠️ 飞书联动规则：所有 push-* 命令均依赖 ../feishu-toolkit/feishu_toolkit.py，
  需配置 FEISHU_APP_ID / FEISHU_APP_SECRET / FEISHU_DEFAULT_CHAT_ID 环境变量。
tools:
  - Bash
  - Read
triggers:
  - 搜索歌曲
  - 查歌词
  - 下载音乐
  - 搜索歌单
  - 推送音乐到飞书
  - 发送卡片
  - 换源
  - 解析链接
  - 分享链接
  - webhook
  - 数据监控
  - 歌单详情
  - 抓取歌单
  - 点赞数
  - 评论数
  - 分享数
  - push playlist
  - search song
  - download music
  - music search
  - parse url
  - share link
  - music detail
  - playlist detail
---

# Music Toolkit Skill

音乐搜索/下载/飞书推送/数据监控工具包。封装 go-music-dl HTTP API。

## 模块速查：我该用哪个命令？

| 用户意图 | 使用模块 | 命令 | 需要后端 |
|---------|---------|------|---------|
| 查看歌单里有哪些歌、统计数据 | 📊 数据监控 | `playlist-detail "<url>"` | 无需 |
| 获取某首歌的收藏/评论/分享数 | 📊 数据监控 | `music-detail "<url>"` | 无需 |
| 把歌单数据推送到飞书群卡片 | 📊+📤 | `push-playlist-detail "<url>"` | 需飞书 |
| **生成飞书多维表格** | 📊+📤 | `playlist-to-table "<url>"` | 需飞书 |
| 下载单首歌曲文件 | 🎵 下载 | `download <id> <source>` | go-music-dl |
| 下载整个歌单 | 🎵 下载 | `download-playlist <id> <source>` | go-music-dl |
| 搜索歌曲 | 🎵 下载 | `search "关键词"` | go-music-dl |

> **关键区别**：`playlist-detail` 只抓数据（不下载音频），`download-playlist` 只下载文件（不抓统计）。这是两个独立的功能，不要混用。

## 工具位置

工具位置: 当前项目根目录下的 `music_toolkit.py`
运行方式: 先 `cd` 到 `music-toolkit/` 项目根目录，再执行下面命令
依赖: `requests` (`pip install requests`)
后端: go-music-dl Docker (`localhost:8080`)（仅下载/搜索功能需要）

---

## ⚠️ 飞书联动说明（AI 必读）

**所有飞书推送功能都通过 feishu-toolkit 实现，不是官方 Feishu MCP。**

### 依赖链

```
用户请求发送飞书卡片/文件/文档
        ↓
music_toolkit.py 的 push-* CLI 命令
或 Python 的 FeishuPusher 类
        ↓
动态导入 ../feishu-toolkit/feishu_toolkit.py
        ↓
feishu_toolkit.FeishuClient → 飞书 Open API
```

### 前置条件

```bash
# 1. feishu-toolkit 必须位于同级目录（或设置环境变量）
ls ../feishu-toolkit/feishu_toolkit.py  # 必须存在

# 或者设置路径
export FEISHU_TOOLKIT_PATH="/path/to/feishu-toolkit"

# 2. 飞书 App 凭证（push-* App API 命令必需）
export FEISHU_APP_ID="cli_xxx"
export FEISHU_APP_SECRET="xxx"
export FEISHU_DEFAULT_CHAT_ID="oc_xxx"   # 默认推送群
```

### Webhook vs App API

| 功能 | Webhook（无需认证） | App API（需凭证） |
|------|:-------------------:|:-----------------:|
| 推送卡片消息 | ✅ push-webhook / parse-url --webhook | ✅ push-song / push-search / push-playlist-detail |
| 发送音频文件 | ❌ | ✅ download-playlist --send-chat / send-to-chat |
| 云盘分片上传 | ❌ | ✅ 自动（>30MB zip） |
| 创建歌词文档 | ❌ | ✅ download-playlist --lyrics-doc |

---

## CLI 命令

### 搜索歌曲
```bash
python music_toolkit.py search "晴天"
python music_toolkit.py search "晴天" --source qq --source netease
python music_toolkit.py search "晴天" --json
```

### 搜索歌单
```bash
python music_toolkit.py search-playlist "周杰伦精选"
python music_toolkit.py search-playlist "周杰伦" --source netease
```

### 获取歌曲详情（inspect + lyrics）
```bash
python music_toolkit.py detail 0042rlGx2WHBrG qq
python music_toolkit.py detail 0042rlGx2WHBrG qq --json
```

### 获取歌词
```bash
python music_toolkit.py lyrics 0042rlGx2WHBrG qq
```

### 下载歌曲
```bash
python music_toolkit.py download 0042rlGx2WHBrG qq
python music_toolkit.py download 0042rlGx2WHBrG qq --name "晴天" --artist "周杰伦"
python music_toolkit.py download 0042rlGx2WHBrG qq --embed --dir ~/Music
```

### 换源搜索
```bash
python music_toolkit.py switch-source --name "晴天" --artist "周杰伦"
python music_toolkit.py switch-source --name "晴天" --artist "周杰伦" --source qq
```

### 查看歌单歌曲
```bash
python music_toolkit.py playlist 6792103822 netease
python music_toolkit.py playlist 6792103822 netease --json
```

### 批量下载歌单
```bash
# 下载歌单所有歌曲（自动换源）
python music_toolkit.py download-playlist 17662978875 netease --dir ~/Music/陶喆

# 下载完成后推送报告到飞书 webhook（无需认证）
python music_toolkit.py download-playlist 17662978875 netease \
  --webhook "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"

# 下载 + 发送 zip 到飞书群 + 创建歌词文档（需 feishu-toolkit + 环境变量）
python music_toolkit.py download-playlist 9582035807 qq \
  --dir ~/Music/歌单 \
  --send-chat oc_xxx \
  --lyrics-doc
```

**自动换源逻辑**: 原平台 inspect → 可用直接下载 → 不可用则 switch_source → 尝试其他所有平台。同时自动下载 .lrc 和 .txt 歌词文件。

### 解析音乐分享链接（parse-url）
```bash
# 解析链接 → 显示歌曲详情 + 歌词
python music_toolkit.py parse-url "https://music.163.com/song?id=28707005"

# 解析链接 + 下载歌曲文件（自动换源）
python music_toolkit.py parse-url "https://music.163.com/song?id=28707005" --download

# 解析链接 + 推送到飞书 webhook（卡片 + 完整歌词，无需认证）
python music_toolkit.py parse-url "https://music.163.com/song?id=28707005" \
  --webhook "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
```

**支持的链接类型**: 网易云 `music.163.com`、QQ音乐 `y.qq.com`、其他平台分享链接。

---

## 数据监控命令（v0.2.0 新增）

这些命令**不需要 go-music-dl 后端**，直接从平台页面抓取数据。

### 单曲详情抓取（music-detail）
```bash
# 抓取歌曲完整统计数据（收藏/评论/分享/播放、音频直链、歌词等）
python music_toolkit.py music-detail "https://qishui.douyin.com/s/ixrhHvct/"

# 同时显示完整歌词
python music_toolkit.py music-detail "https://qishui.douyin.com/s/ixrhHvct/" --lyrics

# 显示同艺人/相关曲目（汽水音乐，无额外请求）
python music_toolkit.py music-detail "https://qishui.douyin.com/s/ixrhHvct/" --related

# JSON 输出
python music_toolkit.py music-detail "https://qishui.douyin.com/s/ixrhHvct/" --json

# 自定义超时
python music_toolkit.py music-detail "https://qishui.douyin.com/s/ixrhHvct/" --timeout 30
```

**支持平台**: 汽水音乐（完整数据）、网易云音乐、QQ音乐

### 批量抓取歌曲详情（music-detail-batch）
```bash
# 多个 URL 空格分隔
python music_toolkit.py music-detail-batch \
  "https://qishui.douyin.com/s/URL1/" \
  "https://qishui.douyin.com/s/URL2/"

# 从文件读取 URL（每行一个，# 开头为注释）
python music_toolkit.py music-detail-batch --file urls.txt --delay 2.0

# JSON 输出
python music_toolkit.py music-detail-batch --file urls.txt --json
```

### 歌单详情抓取（playlist-detail）
```bash
# 获取歌单完整数据（含所有曲目统计）
python music_toolkit.py playlist-detail "https://qishui.douyin.com/s/ixrkNUQa/"

# 同时下载每首歌歌词（.lrc + .txt）
python music_toolkit.py playlist-detail "https://qishui.douyin.com/s/ixrkNUQa/" \
  --lyrics --dir ~/Downloads/lyrics

# JSON 输出（含完整曲目数组）
python music_toolkit.py playlist-detail "https://qishui.douyin.com/s/ixrkNUQa/" --json
```

### 歌单详情 → 飞书多维表格（playlist-to-table）

⚠️ **此命令需要 feishu-toolkit + 环境变量**（见上方飞书联动说明）

```bash
# 抓取歌单数据并创建飞书多维表格（汽水/网易云/QQ音乐通用）
python music_toolkit.py playlist-to-table "https://music.163.com/playlist?id=xxx"
python music_toolkit.py playlist-to-table "https://qishui.douyin.com/s/xxx/"
python music_toolkit.py playlist-to-table "https://y.qq.com/n/ryqq/playlist/xxx"

# 按点赞降序排列
python music_toolkit.py playlist-to-table "<url>" --sort likes

# 创建后向飞书群发送表格链接卡片
python music_toolkit.py playlist-to-table "<url>" --sort likes --chat-id oc_xxx
```

**多维表格字段**: 序号 / 平台 / song_id / 歌名 / 歌手 / 时长 / 专辑 / 发布日期 / 收藏 / 评论 / 分享 / 播放 / 链接（超链接类型，可直接跳转）

**与 push-playlist-detail 的区别**:
- `playlist-to-table`: 只创建多维表格，无群消息（可选加 `--chat-id` 发一条含链接的卡片）
- `push-playlist-detail`: 发飞书卡片消息（含曲目列表），`--with-doc` 时附加创建多维表格

### 歌单详情 + 推送飞书卡片（push-playlist-detail）

⚠️ **此命令需要 feishu-toolkit + 环境变量**（见上方飞书联动说明）

```bash
# 抓取歌单数据并推送到飞书群（需 FEISHU_APP_ID/SECRET/DEFAULT_CHAT_ID）
python music_toolkit.py push-playlist-detail "https://qishui.douyin.com/s/ixrkNUQa/"

# 指定群组
python music_toolkit.py push-playlist-detail "https://qishui.douyin.com/s/ixrkNUQa/" \
  --chat-id oc_xxx

# 按点赞降序排列（默认降序）
python music_toolkit.py push-playlist-detail "https://qishui.douyin.com/s/ixrkNUQa/" \
  --sort likes

# 按日期升序排列
python music_toolkit.py push-playlist-detail "https://qishui.douyin.com/s/ixrkNUQa/" \
  --sort date --asc

# 排序选项: likes / comments / shares / date
# 方向: --desc（降序，默认）/ --asc（升序）
# 限制条数: --max-tracks 20（默认 0 = 全部显示）

# 典型用法：推送两张卡片，一个点赞降序，一个日期升序
python music_toolkit.py push-playlist-detail "https://qishui.douyin.com/s/ixrkNUQa/" --sort likes --desc
python music_toolkit.py push-playlist-detail "https://qishui.douyin.com/s/ixrkNUQa/" --sort date --asc

# 长歌单 + CSV 完整数据导出（--with-doc）
python music_toolkit.py push-playlist-detail "https://qishui.douyin.com/s/ixhJKBKw/" --sort likes --with-doc
```

**飞书卡片样式**:
- Header: 歌单标题，副标题: 创建者 · N 首
- Fields: 更新时间、创建时间、收藏数、分享数、播放数
- 曲目表格：单个 `card_column_set`，左列歌名（weight=6），右列统计数字（weight=4）
  - 左列: `1. **歌名(跳转链接)** — 歌手`
  - 右列: `67.1万　3,468　3.2万`（收藏 评论 分享，超万用万为单位）
  - 200+ 首不触发飞书 30KB 上限（实测 185 首 = 15KB）
  - 按日期排序时额外显示发布日期列
- 底部备注: 数据来源 · 抓取日期 · 排序信息 · CSV 提示
- `--with-doc`: 卡片后追加 CSV 文件（song_id + 全部原始数据，不受卡片条数限制）

**⚠️ 飞书卡片 JSON 不能超过 ~30KB**。当前方案使用单个 column_set + markdown 文本块，200 首约 15KB。如果未来改回 `card_column_set` 每行一个的样式（更精确对齐），需注意 30 首就会达到 20KB。详见 README 的[卡片技术方案与踩坑记录](#card-tech)。

---

## 其他飞书推送命令（均需 feishu-toolkit）

```bash
# 推送单曲详情卡片
python music_toolkit.py push-song <song_id> <source>
python music_toolkit.py push-song <song_id> <source> --chat-id oc_xxx

# 搜索并推送结果卡片
python music_toolkit.py push-search "晴天"
python music_toolkit.py push-search "晴天" --source qq --chat-id oc_xxx

# 推送歌单卡片（基础版，无统计数据）
python music_toolkit.py push-playlist <playlist_id> <source>

# 发送文件到飞书群（单文件直发，多文件自动打包 zip，>30MB 自动云盘分片上传）
python music_toolkit.py send-to-chat ~/Music/*.mp3
python music_toolkit.py send-to-chat ~/Music/ --include-lrc --chat-id oc_xxx
```

## Webhook 推送（无需认证）

```bash
# 搜索歌曲 + 推送到飞书 webhook（卡片 + 歌词）
python music_toolkit.py push-webhook "晴天" "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
python music_toolkit.py push-webhook "晴天" "https://open.feishu.cn/open-apis/bot/v2/hook/xxx" --source qq
```

**Webhook 推送发送两条消息**: 1) 歌曲详情交互卡片  2) 纯文本完整歌词

---

## Python API 用法

```python
from pathlib import Path
import sys
sys.path.insert(0, "/path/to/music-toolkit")
from music_toolkit import (
    MusicClient, FeishuPusher, Song, Playlist,
    SongDetailInfo, PlaylistDetailInfo,
    push_to_webhook, get_song_detail_from_url, get_playlist_detail_from_url
)

client = MusicClient()  # 默认 localhost:8080

# ── 搜索 ──
songs = client.search_songs("晴天", sources=["qq", "netease"])
playlists = client.search_playlists("周杰伦")

# ── 详情 & 歌词 ──
enriched = client.enrich_song(songs[0])   # inspect + lyrics → 完整 Song
lyrics = client.get_lyrics("0042rlGx2WHBrG", "qq")
result = client.inspect("0042rlGx2WHBrG", "qq")
print(result.valid, result.size, result.bitrate)

# ── 换源 ──
alt = client.switch_source("晴天", "周杰伦", source="qq")

# ── 下载 ──
filepath = client.download("0042rlGx2WHBrG", "qq", name="晴天", artist="周杰伦")
lrc_path = client.download_lyrics_file("0042rlGx2WHBrG", "qq", name="晴天", artist="周杰伦")
results = client.download_playlist("9582035807", "qq", save_dir="~/Music")

# ── 歌单歌曲 ──
playlist_songs = client.get_playlist_songs("6792103822", "netease")

# ── 数据监控：从分享链接抓取详情（不需要 go-music-dl）──
detail: SongDetailInfo = get_song_detail_from_url("https://qishui.douyin.com/s/ixrhHvct/")
print(detail.name, detail.favorites, detail.comments, detail.shares)
print(detail.lyrics_text)   # 纯文本歌词（去时间轴）
print(detail.audio_url)     # CDN 直链（~24h 有效）

playlist: PlaylistDetailInfo = get_playlist_detail_from_url("https://qishui.douyin.com/s/ixrkNUQa/")
print(playlist.title, len(playlist.tracks))
for track in playlist.tracks:
    print(f"{track.name} — 点赞:{track.favorites} 评论:{track.comments}")

# ── 飞书推送（Webhook，无需认证）──
push_to_webhook("https://open.feishu.cn/open-apis/bot/v2/hook/xxx", enriched)

# ── 飞书推送（App API，需要 feishu-toolkit + 环境变量）──
# feishu-toolkit 必须位于 ../feishu-toolkit/ 或设置 FEISHU_TOOLKIT_PATH
pusher = FeishuPusher()
pusher.push_song_card(enriched)                      # 单曲卡片
pusher.push_search_results(songs, "晴天")             # 搜索结果卡片
pusher.push_playlist_card(playlist_obj, songs[:5])   # 歌单卡片（基础版）

# 歌单详情卡片（v0.2.0，含统计数据 + 排序）
pusher.push_playlist_detail_card(
    playlist,
    sort_by="likes",    # likes / comments / shares / date
    sort_desc=True,     # True=降序, False=升序
    max_tracks=0,       # 0=全部显示
)

pusher.send_song_files(file_paths, chat_id="oc_xxx")  # 发送文件（自动打包/云盘上传）
doc_url = pusher.create_playlist_lyrics_doc(songs)    # 创建歌词文档
```

---

## 数据模型

### Song（搜索/下载结果）
```python
@dataclass(frozen=True)
class Song:
    id: str          # 歌曲 ID
    source: str      # 平台代码 (qq, netease, soda, ...)
    name: str        # 歌曲名
    artist: str      # 歌手名
    duration: int    # 时长（秒）
    cover: str       # 封面 URL
    album: str       # 专辑名
    lyrics: str      # 歌词 (LRC)
    url: str         # 音频 URL（inspect 后获得）
    size: str        # 文件大小
    bitrate: str     # 码率
    link: str        # 原始链接
    score: float     # 换源匹配度 (0-1)
    extra: dict      # 平台额外数据
```

### SongDetailInfo（数据监控，来自分享链接抓取）
```python
@dataclass(frozen=True)
class SongDetailInfo:
    song_id: str        # 歌曲 ID
    platform: str       # 平台 (soda / netease / qq)
    name: str           # 歌曲名
    artist: str         # 歌手名
    duration: int       # 时长（秒）
    cover: str          # 封面 URL
    album: str          # 专辑名
    album_id: str       # 专辑 ID
    publish_date: str   # 发布日期 YYYY-MM-DD
    favorites: int      # 收藏数
    comments: int       # 评论数
    shares: int         # 分享数
    plays: int          # 播放数
    audio_url: str      # 音频 CDN 直链（~24h 有效，汽水音乐）
    lyrics_lrc: str     # LRC 格式歌词
    genre: str          # 曲风
    language: str       # 语言代码
    composers: str      # 作曲（逗号分隔）
    lyricists: str      # 作词（逗号分隔）
    qualities: str      # 音质选项 (e.g. "medium(68k) / higher(132k) / lossless")
    share_url: str      # 原始分享链接
    resolved_url: str   # 解析后的完整 URL
    extra: dict         # 平台原始数据

    # 计算属性
    # .duration_str → "4:29"
    # .lyrics_text  → 纯文本歌词（去时间轴）
```

### PlaylistDetailInfo（歌单数据监控）
```python
@dataclass(frozen=True)
class PlaylistDetailInfo:
    playlist_id: str    # 歌单 ID
    platform: str       # 平台 (soda)
    title: str          # 歌单名
    creator: str        # 创建者
    cover: str          # 封面 URL
    track_count: int    # 歌曲总数
    create_time: str    # 创建日期 YYYY-MM-DD
    update_time: str    # 更新日期 YYYY-MM-DD
    description: str    # 描述
    tracks: tuple       # tuple[SongDetailInfo]，所有曲目
    share_url: str      # 原始分享链接
    resolved_url: str   # 解析后 URL
    extra: dict         # 含 play_count / collect_count / share_count
```

### Playlist（搜索结果，基础版）
```python
@dataclass(frozen=True)
class Playlist:
    id: str           # 歌单 ID
    source: str       # 平台代码
    name: str         # 歌单名
    cover: str        # 封面 URL
    track_count: int  # 歌曲数
    play_count: int   # 播放量
    creator: str      # 创建者
    description: str  # 描述
```

---

## 支持的平台

| 代码 | 名称 | 代码 | 名称 |
|------|------|------|------|
| netease | 网易云音乐 | soda | Soda/汽水音乐 |
| qq | QQ音乐 | fivesing | 5sing |
| kugou | 酷狗音乐 | jamendo | Jamendo (CC) |
| kuwo | 酷我音乐 | joox | JOOX |
| migu | 咪咕音乐 | bilibili | 哔哩哔哩 |
| qianqian | 千千音乐 | | |

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| GO_MUSIC_DL_URL | go-music-dl 服务地址 | http://localhost:8080 |
| DOWNLOAD_DIR | 下载保存目录 | ./downloads |
| FEISHU_APP_ID | 飞书应用 ID | (App API 推送必需) |
| FEISHU_APP_SECRET | 飞书应用 Secret | (App API 推送必需) |
| FEISHU_DEFAULT_CHAT_ID | 默认飞书群 ID | (App API 推送必需) |
| FEISHU_TOOLKIT_PATH | feishu-toolkit 所在目录 | 自动查找 ../feishu-toolkit |

---

## 常见场景速查

| 场景 | 命令 |
|------|------|
| 搜歌 | `search "晴天"` |
| 下载单曲 | `download <id> <source>` |
| 单曲下载 + 发群 | `download-send <id> <source> --name "晴天" --artist "周杰伦"` |
| 下载歌单 | `download-playlist <id> <source> --dir ~/Music` |
| 下载歌单 + 发群 + 歌词文档 | `download-playlist <id> <source> --send-chat oc_xxx --lyrics-doc` |
| 解析链接并下载 | `parse-url "<url>" --download` |
| **单曲数据监控** | `music-detail "<share_url>"` |
| **歌单数据监控** | `playlist-detail "<share_url>"` |
| **歌单数据 + 推飞书卡片** | `push-playlist-detail "<share_url>" --sort likes` |
| **歌单数据 → 飞书多维表格** | `playlist-to-table "<share_url>" --sort likes` |
| **歌单数据 → 表格 + 通知群** | `playlist-to-table "<share_url>" --sort likes --chat-id oc_xxx` |
| **歌单数据 + 下载歌词** | `playlist-detail "<share_url>" --lyrics --dir ./lyrics` |
| **批量抓取数据** | `music-detail-batch --file urls.txt` |
| 推送到飞书（webhook，无需认证） | `push-webhook "晴天" "<webhook_url>"` |
| 推送到飞书（App API） | `push-search "晴天"` |
| 发文件到群 | `send-to-chat ~/Music/*.mp3` |

---

## 错误处理

所有 CLI 命令出错时输出到 stderr 并返回非零退出码。
Python API 抛出 `MusicClientError` 异常。

```python
from music_toolkit import MusicClient, MusicClientError

try:
    client = MusicClient()
    songs = client.search_songs("test")
except MusicClientError as e:
    print(f"Error: {e}")
    # 常见错误:
    # - "无法连接到 go-music-dl 服务" → Docker 未启动
    # - "feishu_toolkit.py 未找到" → feishu-toolkit 未安装或路径错误
```
