# Music Toolkit

音乐搜索 / 下载 / 飞书推送工具包。

封装 [go-music-dl](https://github.com/guohuiyuan/go-music-dl) HTTP API，聚合 11 个音乐平台，提供搜索、歌词、下载（自动换源）、飞书卡片推送等功能。单文件 + CLI + 可 import，配合 SKILL.md 让 AI 助手一看就会用。

## 架构

```
用户 / AI 助手 (Claude Code)
        │
        │  CLI 或 Python import
        ↓
  music_toolkit.py ─── 核心单文件
        │
   ┌────┴────┐
   ↓         ↓
go-music-dl   feishu-toolkit (可选)
 Docker容器    飞书 App API 推送
 :8080
```

## 支持平台

| 代码 | 名称 | 代码 | 名称 |
|------|------|------|------|
| netease | 网易云音乐 | qianqian | 千千音乐 |
| qq | QQ音乐 | soda | Soda/汽水音乐 |
| kugou | 酷狗音乐 | fivesing | 5sing |
| kuwo | 酷我音乐 | jamendo | Jamendo (CC) |
| migu | 咪咕音乐 | joox | JOOX |
| bilibili | 哔哩哔哩 | | |

## 安装

### 前置依赖

- **Docker** — 运行 go-music-dl 后端
- **Python 3.9+**
- **requests** — `pip install requests`

### 步骤

```bash
# 1. 启动 go-music-dl 后端
docker run -d --name go-music-dl -p 8080:8080 guohuiyuan/go-music-dl:latest

# 2. 克隆项目
git clone https://github.com/mix9581/music-toolkit.git ~/music-toolkit
cd ~/music-toolkit

# 3. 安装依赖
pip install requests

# 4. (可选) 配置环境变量
cp .env.example .env
# 编辑 .env 填入飞书配置等

# 5. 验证
python3 music_toolkit.py platforms
python3 music_toolkit.py search "晴天"
```

## CLI 用法

### 搜索歌曲

```bash
python3 music_toolkit.py search "晴天"
python3 music_toolkit.py search "晴天" --source qq --source netease
python3 music_toolkit.py search "晴天" --json
```

### 搜索歌单

```bash
python3 music_toolkit.py search-playlist "周杰伦精选"
python3 music_toolkit.py search-playlist "周杰伦" --source netease
```

### 歌曲详情 (inspect + 歌词)

```bash
python3 music_toolkit.py detail <song_id> <source>
```

### 获取歌词

```bash
python3 music_toolkit.py lyrics <song_id> <source>
```

### 下载歌曲

```bash
python3 music_toolkit.py download <song_id> <source>
python3 music_toolkit.py download <song_id> <source> --name "晴天" --artist "周杰伦" --dir ~/Music
```

### 换源搜索

```bash
python3 music_toolkit.py switch-source --name "晴天" --artist "周杰伦"
python3 music_toolkit.py switch-source --name "晴天" --artist "周杰伦" --source qq
```

### 解析音乐分享链接

```bash
# 解析链接 → 显示详情 + 歌词
python3 music_toolkit.py parse-url "https://music.163.com/song?id=28707005"

# 解析 + 下载 (自动换源)
python3 music_toolkit.py parse-url "https://music.163.com/song?id=28707005" --download

# 解析 + 推送到飞书 webhook
python3 music_toolkit.py parse-url "https://music.163.com/song?id=28707005" --webhook "<webhook_url>"
```

### 批量下载歌单 (自动换源)

```bash
# 下载歌单所有歌曲
python3 music_toolkit.py download-playlist <playlist_id> <source>

# 指定目录 + 完成后推送飞书报告
python3 music_toolkit.py download-playlist 17662978875 netease --dir ~/Music/陶喆 --webhook "<webhook_url>"
```

自动换源逻辑：对每首歌 → inspect 原平台 → 不可用则 switch_source → 仍失败则全平台搜索 → 穷尽所有源直到成功或全部失败。

### 飞书推送

```bash
# Webhook 推送 (无需认证，推荐)
python3 music_toolkit.py push-webhook "晴天" "<webhook_url>"

# App API 推送 (需配置 FEISHU_APP_ID/SECRET)
python3 music_toolkit.py push-song <song_id> <source>
python3 music_toolkit.py push-search "晴天"
python3 music_toolkit.py push-playlist <playlist_id> <source>
```

### 列出平台

```bash
python3 music_toolkit.py platforms
```

## Python API

```python
from music_toolkit import MusicClient, push_to_webhook

client = MusicClient()  # 默认 localhost:8080

# 搜索
songs = client.search_songs("晴天")
songs = client.search_songs("晴天", sources=["qq", "netease"])
playlists = client.search_playlists("周杰伦")

# 歌词 / 详情
lyrics = client.get_lyrics("0042rlGx2WHBrG", "qq")
result = client.inspect("0042rlGx2WHBrG", "qq")  # → InspectResult
enriched = client.enrich_song(songs[0])            # inspect + lyrics

# 下载
filepath = client.download("0042rlGx2WHBrG", "qq", name="晴天", artist="周杰伦")
lrc_path = client.download_lyrics_file("0042rlGx2WHBrG", "qq", name="晴天")

# 换源
alt = client.switch_source("晴天", "周杰伦", source="qq")

# 歌单批量下载 (自动换源)
results = client.download_playlist("17662978875", "netease", save_dir="~/Music")

# 飞书 Webhook 推送
push_to_webhook("https://open.feishu.cn/open-apis/bot/v2/hook/xxx", enriched)
```

## Claude Code / AI 助手集成

本项目包含 `skill/SKILL.md`，可注册为 Claude Code Skill：

```bash
# 安装为 Claude Code Skill
cp -r ~/music-toolkit/skill ~/.claude/skills/music-toolkit
```

安装后，对 AI 说"搜索歌曲"、"下载音乐"、"解析链接"等自然语言指令，AI 会自动读取 SKILL.md 并调用相应命令。

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `GO_MUSIC_DL_URL` | go-music-dl 服务地址 | `http://localhost:8080` |
| `DOWNLOAD_DIR` | 下载保存目录 | `./downloads` |
| `FEISHU_APP_ID` | 飞书应用 ID | (App API 推送时需要) |
| `FEISHU_APP_SECRET` | 飞书应用 Secret | (App API 推送时需要) |
| `FEISHU_DEFAULT_CHAT_ID` | 默认飞书群 ID | (App API 推送时需要) |

> Webhook 推送不需要环境变量，只需提供 webhook URL。

## 测试

```bash
pip install pytest
python3 -m pytest tests/ -v
```

## License

MIT
