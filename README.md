# Music Toolkit

<p align="center">
  <strong>音乐搜索 / 下载 / 飞书推送工具包</strong><br>
  聚合 11 个平台，单文件 + CLI + Python API，AI Agent 一看就会用
</p>

<p align="center">
  <a href="#quick-start">快速开始</a> ·
  <a href="#playlist-workflow">歌单下载</a> ·
  <a href="#data-monitor">数据监控</a> ·
  <a href="#feishu">飞书推送</a> ·
  <a href="#lyrics-doc">歌词文档</a> ·
  <a href="#api">API 参考</a>
</p>

---

## 架构

```
用户 / AI 助手 (Claude Code / OpenClaw)
        │
        │  CLI 或 Python import
        ▼
  music_toolkit.py ── 核心单文件
        │
   ┌────┴────┐
   ▼         ▼
go-music-dl   feishu-toolkit (可选)
 Docker容器    飞书消息 / 文档 / 云盘
 :8080         github.com/mix9581/feishu-toolkit
```

搭配 [feishu-toolkit](https://github.com/mix9581/feishu-toolkit) 使用可解锁完整能力：歌曲文件发群、歌词文档、歌单报告卡片。

## 支持平台

| 代码 | 名称 | 代码 | 名称 |
|------|------|------|------|
| netease | 网易云音乐 | qianqian | 千千音乐 |
| qq | QQ音乐 | soda | Soda/汽水音乐 |
| kugou | 酷狗音乐 | fivesing | 5sing |
| kuwo | 酷我音乐 | jamendo | Jamendo (CC) |
| migu | 咪咕音乐 | joox | JOOX |
| bilibili | 哔哩哔哩 | | |

<h2 id="quick-start">Quick Start</h2>

### 前置依赖

- **Docker** — 运行 go-music-dl 后端
- **Python 3.9+**
- **requests** — `pip install requests`

### 安装

```bash
# 1. 启动 go-music-dl 后端
docker run -d --name go-music-dl -p 8080:8080 guohuiyuan/go-music-dl:latest

# 2. 克隆项目（可放在任意目录，建议与 feishu-toolkit 同级）
git clone https://github.com/mix9581/music-toolkit.git
cd /path/to/music-toolkit

# 3. 安装依赖
pip install requests

# 4. (可选) 安装 feishu-toolkit — 解锁飞书推送能力
# 建议与 music-toolkit 放在同一父目录；也可设置 FEISHU_TOOLKIT_PATH 指向它
git clone https://github.com/mix9581/feishu-toolkit.git ../feishu-toolkit
export FEISHU_APP_ID="cli_xxx"
export FEISHU_APP_SECRET="xxx"
export FEISHU_DEFAULT_CHAT_ID="oc_xxx"

# 5. 验证
python3 music_toolkit.py platforms
python3 music_toolkit.py search "晴天"
```

<h2 id="playlist-workflow">歌单下载（核心场景）</h2>

### 一键下载整个歌单

```bash
# QQ 音乐歌单
python3 music_toolkit.py download-playlist 9582035807 qq --dir ~/Music/歌单

# 网易云歌单
python3 music_toolkit.py download-playlist 17662978875 netease --dir ~/Music/陶喆

# 汽水音乐歌单（从分享链接提取 playlist_id）
python3 music_toolkit.py download-playlist 7602191490944712731 soda --dir ~/Music/汽水
```

**自动换源**：对每首歌先检查原平台 → 不可用则搜索 11 个平台找替代源 → 穷尽所有源直到成功或全部失败。每首歌同时下载 `.lrc`（带时间轴）和 `.txt`（纯文本歌词）。

### 下载 + 发飞书群 + 歌词文档（完整流程）

```bash
python3 music_toolkit.py download-playlist 9582035807 qq \
  --dir ~/Music/歌单 \
  --send-chat oc_xxx \
  --lyrics-doc
```

这一条命令完成：

```
歌单 URL
  │
  ▼
1. 获取歌单歌曲列表 (25 首)
  │
  ▼
2. 逐首下载 + 自动换源
   ├── 原平台可用 → 直接下载 mp3 + lrc
   └── 原平台不可用 → 搜索 11 个平台找替代源
  │
  ▼
3. 打包 zip (所有 mp3 + lrc)
   ├── zip ≤ 30MB → IM 直接发群
   └── zip > 30MB → 飞书云盘分片上传
       ├── upload_prepare → 获取 upload_id + 分片数
       ├── upload_part × N → 每片 4MB (Adler-32 校验)
       └── upload_finish → 返回 file_token
       → 设置组织内分享权限
       → 发送卡片消息 (含下载链接)
  │
  ▼
4. 创建飞书歌词文档
   ├── 每首歌名为 H1 标题
   ├── 歌词内容为代码块 (方便复制)
   └── 自动设置分享权限
   → 发送文档链接卡片到群
```

**为什么打包成 1 个 zip 而不是逐个发送？**

AI Agent 调用工具时常见的错误做法是逐个上传 20 首歌 → 20 次 API 调用 + 群里 20 条消息。正确做法：

| 方式 | API 调用 | 群消息 | 体验 |
|------|---------|--------|------|
| 逐个发送 20 首 | 20 次 | 20 条 | 刷屏 |
| 打包成 1 个 zip | 1-2 次 | 1 条 | 点击即下载 |

### 下载 + webhook 报告（无需飞书 App 认证）

```bash
python3 music_toolkit.py download-playlist 9582035807 qq \
  --dir ~/Music/歌单 \
  --webhook "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
```

### 单曲下载 + 直接发群（Flow A）

```bash
# 下载单曲并直接发送 mp3 + txt 歌词到飞书群
python3 music_toolkit.py download-send 0039MnYb0qxYhV qq \
  --name "晴天" --artist "周杰伦" --dir ~/Music
```

群里会收到 2 条消息：mp3 音频文件 + txt 纯文本歌词。适合分享单首歌。

<h2 id="feishu">飞书推送</h2>

music-toolkit 通过 [feishu-toolkit](https://github.com/mix9581/feishu-toolkit) 提供两种推送方式：

### 方式 1: Webhook（无需认证，推荐快速使用）

```bash
# 搜索歌曲 → 推送卡片 + 歌词到飞书群
python3 music_toolkit.py push-webhook "晴天" "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"

# 解析链接 → 推送
python3 music_toolkit.py parse-url "https://music.163.com/song?id=28707005" \
  --webhook "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
```

### 方式 2: App API（需配置环境变量，功能更全）

```bash
export FEISHU_APP_ID="cli_xxx"
export FEISHU_APP_SECRET="xxx"
export FEISHU_DEFAULT_CHAT_ID="oc_xxx"

# 推送单曲卡片（含歌词预览、音质、时长）
python3 music_toolkit.py push-song <song_id> <source>

# 搜索 → 推送搜索结果卡片
python3 music_toolkit.py push-search "晴天"

# 推送歌单卡片
python3 music_toolkit.py push-playlist <playlist_id> <source>

# 发送歌曲文件到群（单首直接发，多首打包 zip）
python3 music_toolkit.py send-to-chat ~/Music/*.mp3
```

App API 模式的独有能力（Webhook 无法实现）：

| 能力 | Webhook | App API |
|------|:-------:|:-------:|
| 推送卡片消息 | ✅ | ✅ |
| 发送歌曲文件 | ❌ | ✅ |
| 云盘分片上传（大文件） | ❌ | ✅ |
| 创建歌词文档 | ❌ | ✅ |
| 自定义群组 | ❌ | ✅ 支持多群 |

<h2 id="lyrics-doc">歌词整合文档</h2>

将歌单所有歌词整合成一篇飞书文档，方便查阅和分享：

```bash
# CLI: 下载歌单同时创建歌词文档
python3 music_toolkit.py download-playlist 9582035807 qq \
  --lyrics-doc --send-chat oc_xxx
```

```python
# Python API
from music_toolkit import MusicClient, FeishuPusher

client = MusicClient()
pusher = FeishuPusher()

# 获取歌单并丰富歌词
songs = client.get_playlist_songs("9582035807", "qq")
enriched = [client.enrich_song(s) for s in songs]

# 创建歌词文档
doc_url = pusher.create_playlist_lyrics_doc(
    enriched,
    title="歌单歌词 - 9582035807",
)
print(f"文档地址: {doc_url}")
```

文档结构：

```
📄 歌单歌词 - 9582035807
├── H1: What?? - Kevin MacLeod
│   ├── 时长: 2:10 | 平台: QQ音乐 | 专辑: ...
│   └── [歌词代码块]
├── ── 分割线 ──
├── H1: 欢沁 - 林海
│   ├── 时长: 3:45 | 平台: QQ音乐
│   └── [歌词代码块]
└── ...
```

## 搜索 & 下载

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

### 下载单首歌曲

```bash
python3 music_toolkit.py download <song_id> <source>
python3 music_toolkit.py download <song_id> <source> --name "晴天" --artist "周杰伦" --dir ~/Music
```

### 解析音乐分享链接

```bash
# 解析 → 显示详情 + 歌词
python3 music_toolkit.py parse-url "https://music.163.com/song?id=28707005"

# 解析 → 下载（自动换源）
python3 music_toolkit.py parse-url "https://music.163.com/song?id=28707005" --download

# 解析 → 推送到飞书
python3 music_toolkit.py parse-url "https://music.163.com/song?id=28707005" --webhook "<url>"
```

支持的链接：网易云 `music.163.com`、QQ音乐 `y.qq.com`、其他平台分享链接。

<h2 id="data-monitor">数据监控</h2>

### 歌曲详情抓取

从平台分享链接抓取歌曲的完整统计数据（收藏/评论/分享/播放、音频直链、歌词等），无需 go-music-dl 服务。

```bash
# 单曲详情（汽水 / 网易云 / QQ音乐）
python3 music_toolkit.py music-detail "https://qishui.douyin.com/s/ixrhHvct/"

# 同时显示完整歌词
python3 music_toolkit.py music-detail "https://qishui.douyin.com/s/ixrhHvct/" --lyrics

# 显示同艺人 / 相关曲目（汽水音乐，无额外请求）
python3 music_toolkit.py music-detail "https://qishui.douyin.com/s/ixrhHvct/" --related

# 输出 JSON 方便程序处理
python3 music_toolkit.py music-detail "https://qishui.douyin.com/s/ixrhHvct/" --json
```

输出字段示例（汽水音乐）：歌曲 ID、歌手、专辑、时长、发布日期、曲风、语言、作曲/作词、音质选项、封面、音频直链（~24h 有效）、收藏/评论/分享数、完整 LRC 歌词。

> **单曲详情 (`music-detail`) 各平台数据差异**：汽水音乐返回完整统计数据；网易云和 QQ 音乐返回基础信息（歌名/歌手/专辑/时长/封面），互动统计有限。详见下方歌单详情的[各平台数据能力对比](#各平台数据能力对比)。

### 歌单详情抓取 + 飞书推送

从歌单分享链接获取歌单统计数据和全部曲目信息，**只抓数据，不下载音乐**（可选下载歌词 `.lrc`）。

```bash
# 汽水音乐歌单（含完整曲目统计：收藏/评论/分享）
python3 music_toolkit.py playlist-detail "https://qishui.douyin.com/s/ixrkNUQa/"

# 网易云歌单（含评论数，收藏/分享不可用）
python3 music_toolkit.py playlist-detail "https://music.163.com/playlist?id=17662978875"

# QQ 音乐歌单（基础信息，单曲统计不可用）
python3 music_toolkit.py playlist-detail "https://y.qq.com/n/ryqq_v2/playlist/9582035807"

# 同时下载每首歌的歌词文件（.lrc + .txt）
python3 music_toolkit.py playlist-detail "https://qishui.douyin.com/s/ixrkNUQa/" \
  --lyrics --dir ~/Downloads/lyrics

# 输出 JSON（含完整曲目数组）
python3 music_toolkit.py playlist-detail "https://qishui.douyin.com/s/ixrkNUQa/" --json

# 抓取后直接推送到飞书群（需配置 App 环境变量）
python3 music_toolkit.py push-playlist-detail "https://qishui.douyin.com/s/ixrkNUQa/"
```

#### 各平台数据能力对比

不同平台的公开 API 开放程度差异很大，直接决定了能抓到的数据粒度：

| 数据项 | 汽水音乐 | 网易云 | QQ音乐 | 酷狗 |
|--------|:--------:|:------:|:------:|:----:|
| 歌单基本信息 | ✅ | ✅ | ✅ | ❌ |
| 曲目列表 | ✅ | ✅ | ✅ | ❌ |
| 单曲评论数 | ✅ | ✅ batch API | ❌ | ❌ |
| 单曲收藏数 | ✅ | ❌ | ❌ | ❌ |
| 单曲分享数 | ✅ | ❌ | ❌ | ❌ |
| 发布日期 | ✅ | ✅ | ✅ | ❌ |
| 实现方式 | SSR 页面内嵌 `_ROUTER_DATA`，一次 GET 全拿 | `/api/v6/playlist/detail` + `/api/batch` 批量评论 | `fcg_ucc_getcdinfo_byids_cp.fcg` 旧版 API | 签名密钥已更新，无可用公开 API |

**为什么汽水能拿全部数据？** 汽水音乐采用服务端渲染 (SSR)，打开分享链接时服务器直接将所有统计数据写入 HTML 的 `_ROUTER_DATA` 变量。网易云和 QQ 音乐是纯 SPA 架构，数据靠前端 JS 异步加载，公开 API 有选择性地封锁了互动统计。

所有实现均为纯 HTTP 请求，**无需 cookie / 登录 / 特殊环境**，任何机器都可运行。

CLI 输出示例（演示歌单：[w. — w.](https://qishui.douyin.com/s/ixrkNUQa/)，27 首）：

```
────────────────────────────────────────────────────────────
📋  w.
────────────────────────────────────────────────────────────
   创建者:  w .
   歌曲数:  27
   平台:    Soda音乐 [soda]
   歌单ID:  7598064834160525338
   创建:    2026-01-26
   更新:    2026-03-31

  #    歌名                       歌手     收藏        评论      分享
  1    定数                       w.      16,260        69       549
  2    一定要拥有吗               w.      28,366       216     2,683
  6    凝视                       w.     263,396     1,853    10,439
  ...
  27   过期的伞                   w.     361,689     8,497    24,806
```

飞书卡片效果（`push-playlist-detail`）：

- Header 显示歌单名，副标题显示创建者和曲目总数
- Fields 区域：更新时间、收藏数、分享数
- 曲目列表：序号 · **歌名（蓝色跳转链接）** — 歌手  点赞 xx  评论 xx  分享 xx
- 底部备注：数据来源 + 抓取日期

批量抓取多首歌曲详情：

```bash
# 多个 URL 空格分隔
python3 music_toolkit.py music-detail-batch \
  "https://qishui.douyin.com/s/URL1/" \
  "https://qishui.douyin.com/s/URL2/"

# 从文件读取 URL��每行一个，# 开头为注释）
python3 music_toolkit.py music-detail-batch --file urls.txt --delay 2.0
```

### 换源搜索

```bash
python3 music_toolkit.py switch-source --name "晴天" --artist "周杰伦"
```

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
| **歌单数据监控** | `playlist-detail "<share_url>"` (汽水/网易云/QQ) |
| **歌单数据 + 推飞书** | `push-playlist-detail "<share_url>"` |
| **歌单数据 + 下载歌词** | `playlist-detail "<share_url>" --lyrics --dir ./lyrics` |
| **批量抓取数据** | `music-detail-batch --file urls.txt` |
| 推送到飞书 (webhook) | `push-webhook "晴天" "<webhook_url>"` |
| 推送到飞书 (App API) | `push-search "晴天"` |
| 发文件到群 | `send-to-chat ~/Music/*.mp3` |

> 先进入项目目录：`cd /path/to/music-toolkit`
> 所有命令前缀: `python3 music_toolkit.py`

<h2 id="api">Python API</h2>

```python
from music_toolkit import MusicClient, FeishuPusher, push_to_webhook

client = MusicClient()  # 默认 localhost:8080

# ── 搜索 ──
songs = client.search_songs("晴天", sources=["qq", "netease"])
playlists = client.search_playlists("周杰伦")

# ── 详情 & 歌词 ──
enriched = client.enrich_song(songs[0])  # inspect + lyrics
lyrics = client.get_lyrics("0042rlGx2WHBrG", "qq")

# ── 下载 ──
filepath = client.download("0042rlGx2WHBrG", "qq", name="晴天", artist="周杰伦")
results = client.download_playlist("9582035807", "qq", save_dir="~/Music")

# ── 换源 ──
alt = client.switch_source("晴天", "周杰伦", source="qq")

# ── 飞书推送 (Webhook, 无需认证) ──
push_to_webhook("https://open.feishu.cn/.../hook/xxx", enriched)

# ── 飞书推送 (App API, 需要 feishu-toolkit + 环境变量) ──
pusher = FeishuPusher()
pusher.push_song_card(enriched)                   # 推送单曲卡片
pusher.push_search_results(songs, "晴天")          # 推送搜索结果卡片
pusher.push_playlist_card(playlist, songs[:5])     # 推送歌单卡片
pusher.send_song_files(file_paths, chat_id="oc_x") # 发送文件到群 (自动打包)
pusher.create_playlist_lyrics_doc(songs, "歌词")   # 创建歌词文档
```

## Claude Code / AI 助手集成

本项目包含 `skill/SKILL.md`，可注册为 Claude Code Skill：

```bash
# 安装为 Claude Code Skill
cp -r ./skill ~/.claude/skills/music-toolkit
```

安装后，对 AI 说 "搜索歌曲"、"下载歌单"、"推送到飞书" 等自然语言指令即可。

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

## 实测验证

以下示例均经过真实环境验证（2026-03-30）：

### Flow A: 单曲下载 + 发群

```bash
python3 music_toolkit.py download-send 0039MnYb0qxYhV qq \
  --name "晴天" --artist "周杰伦" --dir ~/Music/test_single
```

结果：群里收到 mp3 文件 + txt 纯文本歌词（无时间轴，方便复制）。

### Flow B: 歌单下载 + zip 发群 + 歌词文档

| 平台 | 歌单 | 歌曲数 | 成功率 | zip 大小 | 歌词文档 |
|------|------|--------|--------|----------|----------|
| QQ音乐 | `9582035807` | 25 首 | 25/25 | 122 MB (30 片) | [文档链接](https://feishu.cn/docx/TIFbdZEndoR62Rx8T4Vc1Cldntc) |
| 网易云 | `17662978875` | 15 首 | 15/15 | 68 MB (18 片) | [文档链接](https://feishu.cn/docx/UtcmdpvYioJQFIxUEaEcVCYYnOf) |
| 汽水音乐 | `7602191490944712731` | 112 首 | 112/112 | 849 MB (206 片) | [文档链接](https://feishu.cn/docx/Gxu0dI2Kso8px1xkvnYckeTvnYd) |

```bash
# QQ 音乐
python3 music_toolkit.py download-playlist 9582035807 qq \
  --dir ~/Music/qq --send-chat oc_xxx --lyrics-doc

# 网易云音乐
python3 music_toolkit.py download-playlist 17662978875 netease \
  --dir ~/Music/netease --send-chat oc_xxx --lyrics-doc

# 汽水音乐（从分享链接 https://qishui.douyin.com/s/i9AVQFPK/ 提取 ID）
python3 music_toolkit.py download-playlist 7602191490944712731 soda \
  --dir ~/Music/soda --send-chat oc_xxx --lyrics-doc
```

每首歌下载 3 个文件：`.mp3`（音频）+ `.lrc`（带时间轴歌词）+ `.txt`（纯文本歌词）。zip 打包后通过飞书云盘分片上传，群内收到 1 条卡片消息（含下载链接）+ 1 条歌词文档链接。

## License

MIT
