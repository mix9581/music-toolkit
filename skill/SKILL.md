---
name: music-toolkit
description: |
  当用户要求搜索歌曲、查看歌词、下载音乐、查看歌单、
  换源搜索、推送音乐数据到飞书、解析音乐分享链接时，使用此技能。
tools:
  - Bash
  - Read
triggers:
  - 搜索歌曲
  - 查歌词
  - 下载音乐
  - 搜索歌单
  - 推送音乐到飞书
  - 换源
  - 解析链接
  - 分享链接
  - search song
  - download music
  - music search
  - parse url
  - share link
  - webhook
---

# Music Toolkit Skill

音乐搜索/下载/飞书推送工具包。封装 go-music-dl HTTP API。

## 快速参考

工具位置: 当前项目根目录下的 `music_toolkit.py`
运行方式: 先 `cd` 到 `music-toolkit/` 项目根目录，再执行下面命令
依赖: `requests` (pip install requests)
后端: go-music-dl Docker (localhost:8080)

## CLI 命令

### 搜索歌曲
```bash
# 全平台搜索
python music_toolkit.py search "晴天"

# 指定平台搜索
python music_toolkit.py search "晴天" --source qq
python music_toolkit.py search "晴天" --source qq --source netease

# JSON 输出（适合程序解析）
python music_toolkit.py search "晴天" --json
```

### 搜索歌单
```bash
python music_toolkit.py search-playlist "周杰伦精选"
python music_toolkit.py search-playlist "周杰伦" --source netease
```

### 获取歌曲详情（inspect + lyrics）
```bash
python music_toolkit.py detail <song_id> <source>
# 例:
python music_toolkit.py detail 0042rlGx2WHBrG qq
```

### 获取歌词
```bash
python music_toolkit.py lyrics <song_id> <source>
# 例:
python music_toolkit.py lyrics 0042rlGx2WHBrG qq
```

### 下载歌曲
```bash
python music_toolkit.py download <song_id> <source>

# 指定歌名和歌手（用于文件名）
python music_toolkit.py download 0042rlGx2WHBrG qq --name "晴天" --artist "周杰伦"

# 嵌入封面
python music_toolkit.py download 0042rlGx2WHBrG qq --embed

# 指定保存目录
python music_toolkit.py download 0042rlGx2WHBrG qq --dir /tmp/music
```

### 换源搜索
```bash
python music_toolkit.py switch-source --name "晴天" --artist "周杰伦"
python music_toolkit.py switch-source --name "晴天" --artist "周杰伦" --source qq
```

### 查看歌单歌曲
```bash
python music_toolkit.py playlist <playlist_id> <source>
# 例:
python music_toolkit.py playlist 6792103822 netease
```

### 批量下载歌单（download-playlist）
```bash
# 下载歌单所有歌曲（自动换源，如原平台不可用会尝试其他平台）
python music_toolkit.py download-playlist <playlist_id> <source>

# 指定保存目录
python music_toolkit.py download-playlist 17662978875 netease --dir ~/Music/陶喆

# 下载完成后推送报告到飞书 webhook
python music_toolkit.py download-playlist 17662978875 netease --webhook "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"

# JSON 输出（每首歌的下载结果）
python music_toolkit.py download-playlist 17662978875 netease --json
```

**自动换源逻辑**: 对每首歌 → inspect 原平台 → 可用直接下载 → 不可用则 switch_source 找替代 → 下载。同时自动下载歌词文件 (.lrc)。

### 解析音乐分享链接（parse-url）
```bash
# 解析链接 → 显示歌曲详情 + 歌词
python music_toolkit.py parse-url "https://music.163.com/song?id=28707005"

# 解析链接 + 下载歌曲文件（自动换源）
python music_toolkit.py parse-url "https://music.163.com/song?id=28707005" --download

# 解析链接 + 推送到飞书 webhook（卡片 + 纯文本歌词）
python music_toolkit.py parse-url "https://music.163.com/song?id=28707005" --webhook "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"

# 解析 + 下载 + 推送
python music_toolkit.py parse-url "https://music.163.com/song?id=28707005" --download --webhook "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"

# JSON 输出
python music_toolkit.py parse-url "https://music.163.com/song?id=28707005" --json
```

**parse-url 支持的链接类型**：
- 网易云: `https://music.163.com/song?id=xxx`
- QQ音乐: `https://y.qq.com/n/ryqq/songDetail/xxx`
- 其他平台的分享链接

**自动换源**: 如果原平台资源不可用 (`valid: false`)，会自动在其他平台查找可下载源。

### 列出平台
```bash
python music_toolkit.py platforms
```

### 飞书推送（App API，需配置 FEISHU_APP_ID/SECRET）
```bash
# 推送单曲详情卡片
python music_toolkit.py push-song <song_id> <source>

# 搜索并推送结果卡片
python music_toolkit.py push-search "晴天"
python music_toolkit.py push-search "晴天" --source qq

# 推送歌单卡片
python music_toolkit.py push-playlist <playlist_id> <source>

# 指定飞书群
python music_toolkit.py push-song <song_id> <source> --chat-id oc_xxx
```

### 飞书 Webhook 推送（无需认证，只需 webhook URL）
```bash
# 搜索歌曲 + 推送到飞书 webhook（卡片 + 歌词）
python music_toolkit.py push-webhook "晴天" "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
python music_toolkit.py push-webhook "晴天" "https://open.feishu.cn/open-apis/bot/v2/hook/xxx" --source qq
```

**Webhook 推送发送两条消息**：
1. 交互卡片：歌名、歌手、时长、平台、音质、歌词预览
2. 纯文本：完整歌词（LRC 自动转纯文本）

## Python API 用法

```python
from pathlib import Path
import sys
sys.path.insert(0, str(Path.cwd()))
from music_toolkit import MusicClient, FeishuPusher, Song, push_to_webhook

# 初始化客户端
client = MusicClient()  # 默认 localhost:8080

# 搜索歌曲
songs = client.search_songs("晴天")
songs = client.search_songs("晴天", sources=["qq", "netease"])

# 搜索歌单
playlists = client.search_playlists("周杰伦")

# 获取歌词
lyrics = client.get_lyrics("0042rlGx2WHBrG", "qq")

# 检查歌曲资源
result = client.inspect("0042rlGx2WHBrG", "qq")
print(result.valid, result.size, result.bitrate)

# 换源
alt = client.switch_source("晴天", "周杰伦", source="qq")

# 获取完整详情（inspect + lyrics）
enriched = client.enrich_song(songs[0])

# 下载歌曲（支持 extra 参数用于特定平台）
filepath = client.download("0042rlGx2WHBrG", "qq", name="晴天", artist="周杰伦")

# 下载歌词文件
lrc_path = client.download_lyrics_file("0042rlGx2WHBrG", "qq", name="晴天", artist="周杰伦")

# 获取歌单歌曲
playlist_songs = client.get_playlist_songs("6792103822", "netease")

# 解析分享链接（URL 作为搜索关键词）
songs = client.search_songs("https://music.163.com/song?id=28707005")
if songs:
    enriched = client.enrich_song(songs[0])
    print(enriched.name, enriched.artist, enriched.album)

# ── 飞书推送 ──

# 方式 1: Webhook 推送（无需认证，推荐快速使用）
push_to_webhook("https://open.feishu.cn/open-apis/bot/v2/hook/xxx", enriched)

# 方式 2: App API 推送（需要配置环境变量）
pusher = FeishuPusher()
pusher.push_song_card(enriched)
pusher.push_search_results(songs, "晴天")
doc_url = pusher.create_song_document(enriched)
```

## 支持的平台

| 代码 | 名称 |
|------|------|
| netease | 网易云音乐 |
| qq | QQ音乐 |
| kugou | 酷狗音乐 |
| kuwo | 酷我音乐 |
| migu | 咪咕音乐 |
| qianqian | 千千音乐 |
| soda | Soda音乐 |
| fivesing | 5sing |
| jamendo | Jamendo (CC) |
| joox | JOOX |
| bilibili | 哔哩哔哩 |

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| GO_MUSIC_DL_URL | go-music-dl 服务地址 | http://localhost:8080 |
| DOWNLOAD_DIR | 下载保存目录 | ./downloads |
| FEISHU_APP_ID | 飞书应用 ID | (App API 推送必需) |
| FEISHU_APP_SECRET | 飞书应用 Secret | (App API 推送必需) |
| FEISHU_DEFAULT_CHAT_ID | 默认飞书群 ID | (App API 推送必需) |

**注意**: Webhook 推送不需要环境变量，只需提供 webhook URL。

## 常见场景

### 场景 1: 搜索 → 查看详情 → 下载
```bash
python music_toolkit.py search "晴天" --source qq
# 从结果中记下 song_id
python music_toolkit.py detail 0042rlGx2WHBrG qq
python music_toolkit.py download 0042rlGx2WHBrG qq --name "晴天" --artist "周杰伦"
```

### 场景 2: 分享链接 → 一键获取所有信息 + 下载
```bash
# 最常用！用户给一个分享链接，自动获取详情、歌词、下载
python music_toolkit.py parse-url "https://music.163.com/song?id=28707005" --download
```

### 场景 3: 分享链接 → 推送到飞书
```bash
python music_toolkit.py parse-url "https://music.163.com/song?id=28707005" --webhook "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
```

### 场景 4: 搜索 → 推送飞书（webhook，无需认证）
```bash
python music_toolkit.py push-webhook "晴天" "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
```

### 场景 5: 搜索 → 推送飞书（App API）
```bash
python music_toolkit.py push-search "晴天"
```

### 场景 6: 换源并下载
```bash
python music_toolkit.py switch-source --name "晴天" --artist "周杰伦"
# 从结果中获取新平台的 song_id
python music_toolkit.py download <new_id> <new_source>
```

### 场景 7: 歌单浏览
```bash
python music_toolkit.py search-playlist "周杰伦" --source netease
python music_toolkit.py playlist 6792103822 netease
```

## 数据模型

### Song
```python
@dataclass(frozen=True)
class Song:
    id: str          # 歌曲 ID
    source: str      # 平台代码 (qq, netease, ...)
    name: str        # 歌曲名
    artist: str      # 歌手名
    duration: int    # 时长（秒）
    cover: str       # 封面 URL
    album: str       # 专辑名
    lyrics: str      # 歌词 (LRC)
    url: str         # 音频 URL
    size: str        # 文件大小
    bitrate: str     # 码率
    link: str        # 原始链接
    score: float     # 匹配度 (0-1)
    extra: dict      # 额外数据
```

### Playlist
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
```
