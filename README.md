# Music Toolkit

<p align="center">
  <strong>音乐搜索 / 下载 / 飞书推送工具包</strong><br>
  聚合 11 个平台，单文件 + CLI + Python API，AI Agent 一看就会用
</p>

<p align="center">
  <a href="#quick-start">快速开始</a> ·
  <a href="#mode-1-download">模式1: 歌曲下载</a> ·
  <a href="#mode-2-data-scraping">模式2: 数据抓取</a> ·
  <a href="#feishu">飞书推送</a> ·
  <a href="#api">API 参考</a>
</p>

---

## 🎯 两种核心模式

### 模式 1: 歌曲下载模式
**用途**: 下载单曲或歌单的音频文件 + 歌词，可选发送到飞书群
**输出**: MP3 文件 + LRC/TXT 歌词文件
**飞书集成**:
- 小文件 (≤30MB): 直接发送到群聊
- 大文件 (>30MB): 自动分片上传到飞书云盘 + 发送下载卡片
- 可选创建歌词文档（每首歌一个标题 + 代码块）

### 模式 2: 数据抓取模式
**用途**: 抓取歌单或单曲的元数据（播放量、评论数、收藏数等），不下载音频
**输出**: JSON 数据 + CSV 报表
**飞书集成**:
- 发送数据卡片到群聊（表格形式展示关键指标）
- 使用 feishu-toolkit 的富文本卡片能力

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
- **(可选) KuGouMusicApi** — 获取酷狗完整歌单（突破 SSR 限制）
- **(可选) feishu-toolkit** — 解锁飞书推送能力

### 安装

```bash
# 1. 启动 go-music-dl 后端
docker run -d --name go-music-dl -p 8080:8080 guohuiyuan/go-music-dl:latest

# 2. (可选) 启动 KuGouMusicApi 服务 — 获取酷狗完整歌单
docker-compose -f docker-compose.kugou-api.yml up -d

# 3. 克隆项目（建议与 feishu-toolkit 同级）
git clone https://github.com/mix9581/music-toolkit.git
cd music-toolkit

# 4. 安装依赖
pip install requests

# 5. (可选) 配置 KuGouMusicApi 地址（默认 http://localhost:3000）
export KUGOU_API_URL="http://localhost:3000"

# 6. (可选) 安装 feishu-toolkit — 解锁飞书推送能力
git clone https://github.com/mix9581/feishu-toolkit.git ../feishu-toolkit

# 7. (可选) 配置飞书应用凭证
export FEISHU_APP_ID="cli_xxx"
export FEISHU_APP_SECRET="xxx"

# 8. (可选) 交互式选择飞书群聊
python3 music_toolkit.py setup-chat

# 9. 验证
python3 music_toolkit.py platforms
python3 music_toolkit.py search "晴天"
```

### 酷狗歌单增强（KuGouMusicApi）

默认情况下，酷狗歌单抓取受 SSR 限制，每次最多返回 10 首歌曲。启动 KuGouMusicApi 服务后，可以获取完整歌单：

**优势**：
- ✅ 突破 SSR 限制，获取歌单所有歌曲
- ✅ 无需 Cookie，公开歌单直接访问
- ✅ 稳定可靠，基于官方 API 封装
- ✅ 自动回退，API 不可用时使用网页抓取

**使用方式**：

```bash
# 方式 1: Docker Compose（推荐）
docker-compose -f docker-compose.kugou-api.yml up -d

# 方式 2: 手动启动
git clone https://github.com/MakcRe/KuGouMusicApi.git
cd KuGouMusicApi
npm install
npm run dev

# 验证服务
curl http://localhost:3000/playlist/detail?ids=collection_3_1863870844_4_0

# 使用（自动检测，无需额外配置）
python3 music_toolkit.py playlist-detail "https://www.kugou.com/songlist/gcid_xxx/"
```

**工作原理**：
1. 优先尝试使用 KuGouMusicApi（如果 `KUGOU_API_URL` 可用）
2. API 不可用时自动回退到网页抓取（最多 10 首）
3. 对用户完全透明，无需修改命令

### Cookie 管理（访问会员歌曲/完整歌单）

部分平台需要登录态才能访问完整内容（如酷狗完整歌单、QQ音乐会员歌曲等）。music-toolkit 支持通过 Cookie 管理功能设置登录凭证。

#### 方式 1: 命令行设置（推荐）

```bash
# 查看当前 Cookie 配置
python3 music_toolkit.py cookie list

# 设置单个平台 Cookie
python3 music_toolkit.py cookie set netease "MUSIC_U=your_cookie_here"
python3 music_toolkit.py cookie set qq "uin=123456; qm_keyst=xxx"

# 删除指定平台 Cookie
python3 music_toolkit.py cookie delete netease qq

# 清除所有 Cookie
python3 music_toolkit.py cookie clear
```

#### 方式 2: 从环境变量加载

```bash
# 设置环境变量
export NETEASE_COOKIE="MUSIC_U=xxx"
export QQ_MUSIC_COOKIE="uin=xxx; qm_keyst=xxx"
export KUGOU_COOKIE="xxx"

# 加载到 go-music-dl
python3 music_toolkit.py cookie load --env
```

#### 方式 3: 从 JSON 文件加载

创建 `.music_cookies.json` 文件：

```json
{
  "netease": "MUSIC_U=your_cookie_here",
  "qq": "uin=123456; qm_keyst=xxx",
  "kugou": "your_kugou_cookie"
}
```

加载 Cookie：

```bash
# 从默认文件加载
python3 music_toolkit.py cookie load

# 从指定文件加载
python3 music_toolkit.py cookie load --file my_cookies.json

# 保存当前 Cookie 到文件
python3 music_toolkit.py cookie save --file backup.json
```

#### 如何获取 Cookie？

1. **浏览器开发者工具**:
   - 打开音乐平台网站并登录
   - 按 F12 打开开发者工具
   - 切换到 "Network" 标签
   - 刷新页面，找到任意请求
   - 在 Request Headers 中找到 `Cookie` 字段
   - 复制完整 Cookie 字符串

2. **支持的平台**:
   - `netease` - 网易云音乐
   - `qq` - QQ音乐
   - `kugou` - 酷狗音乐
   - `kuwo` - 酷我音乐
   - `migu` - 咪咕音乐
   - `bilibili` - 哔哩哔哩

3. **Cookie 存储位置**:
   - Cookie 保存在 go-music-dl 的数据库中 (`data/cookies.json`)
   - 重启 Docker 容器后仍然有效
   - 可以随时通过 `cookie list` 查看当前配置

#### 使用示例

```bash
# 1. 设置网易云 Cookie（访问会员歌曲）
python3 music_toolkit.py cookie set netease "MUSIC_U=xxx"

# 2. 设置酷狗 Cookie（获取完整歌单，默认只返回前10首）
python3 music_toolkit.py cookie set kugou "xxx"

# 3. 验证 Cookie 是否生效
python3 music_toolkit.py cookie list

# 4. 下载需要会员的歌曲
python3 music_toolkit.py download SONG_ID netease

# 5. 获取酷狗完整歌单（超过10首）
python3 music_toolkit.py download-playlist PLAYLIST_ID kugou
```

---

### 飞书群聊配置（推荐方式）

使用 `setup-chat` 命令可以交互式选择飞书群聊，无需手动记忆 Chat ID：

```bash
# 1. 设置飞书应用凭证（仅需一次）
export FEISHU_APP_ID="cli_xxx"
export FEISHU_APP_SECRET="xxx"

# 2. 运行交互式配置
python3 music_toolkit.py setup-chat

# 输出示例：
# 🔍 正在获取群聊列表...
#
# 📋 找到 5 个群聊:
#
# 序号   群聊名称                                  Chat ID
# ────────────────────────────────────────────────────────────────────────────
# 1      音乐分享群                                oc_abc123...
# 2      测试群                                    oc_def456...
# 3      工作群                                    oc_ghi789...
#
# 请选择群聊序号 (1-5, 或按 Ctrl+C 取消): 1
#
# ✅ 已选择: 音乐分享群
#    Chat ID: oc_abc123...
#
# 💾 配置已保存到: ~/.config/music-toolkit/config.json
#
# 📝 请将以下内容添加到你的 shell 配置文件 (~/.bashrc 或 ~/.zshrc):
#    export FEISHU_DEFAULT_CHAT_ID="oc_abc123..."

# 3. 将 Chat ID 添加到环境变量（永久生效）
echo 'export FEISHU_DEFAULT_CHAT_ID="oc_abc123..."' >> ~/.zshrc
source ~/.zshrc

# 4. 现在可以直接使用飞书推送功能，无需每次指定 --chat-id
python3 music_toolkit.py download-send 0039MnYb0qxYhV qq --name "晴天" --artist "周杰伦"
```

**仅列出群聊（不保存配置）**：

```bash
python3 music_toolkit.py setup-chat --list-only
```

**更换接收消息的群聊**：

```bash
# 重新运行 setup-chat 即可选择新的群聊
python3 music_toolkit.py setup-chat
```

---

<h2 id="mode-1-download">模式 1: 歌曲下载模式</h2>

### 场景 A: 单曲下载 + 发飞书群

```bash
# 下载单曲并直接发送 mp3 + txt 歌词到飞书群
python3 music_toolkit.py download-send 0039MnYb0qxYhV qq \
  --name "晴天" --artist "周杰伦" --dir ~/Music
```

**输出**: 群里收到 2 条消息（mp3 音频 + txt 歌词）

### 场景 B: 歌单下载（本地保存）

```bash
# QQ 音乐歌单
python3 music_toolkit.py download-playlist 9582035807 qq --dir ~/Music/歌单

# 网易云歌单
python3 music_toolkit.py download-playlist 17662978875 netease --dir ~/Music/陶喆

# 汽水音乐歌单
python3 music_toolkit.py download-playlist 7602191490944712731 soda --dir ~/Music/汽水
```

**自动换源**: 原平台不可用时自动搜索 11 个平台找替代源，每首歌同时下载 `.lrc`（带时间轴）和 `.txt`（纯文本歌词）。

### 场景 C: 歌单下载 + 飞书完整推送（推荐）

```bash
python3 music_toolkit.py download-playlist 9582035807 qq \
  --dir ~/Music/歌单 \
  --send-chat oc_xxx \
  --lyrics-doc
```

**完整流程**:

```
1. 获取歌单歌曲列表 (25 首)
   ↓
2. 逐首下载 + 自动换源
   ├── 原平台可用 → 直接下载 mp3 + lrc
   └── 原平台不可用 → 搜索 11 个平台找替代源
   ↓
3. 打包 zip (所有 mp3 + lrc)
   ├── zip ≤ 30MB → IM 直接发群
   └── zip > 30MB → 飞书云盘分片上传
       ├── upload_prepare → 获取 upload_id + 分片数
       ├── upload_part × N → 每片 4MB (Adler-32 校验)
       └── upload_finish → 返回 file_token
       → 设置组织内分享权限
       → 发送卡片消息 (含下载链接)
   ↓
4. 创建飞书歌词文档
   ├── 每首歌名为 H1 标题
   ├── 歌词内容为代码块 (方便复制)
   └── 自动设置分享权限
   → 发送文档链接卡片到群
```

**为什么打包成 1 个 zip？**

| 方式 | API 调用 | 群消息 | 体验 |
|------|---------|--------|------|
| 逐个发送 20 首 | 20 次 | 20 条 | 刷屏 |
| 打包成 1 个 zip | 1-2 次 | 1 条 | 点击即下载 |

### 场景 D: 歌单下载 + Webhook 报告（无需飞书 App 认证）

```bash
python3 music_toolkit.py download-playlist 9582035807 qq \
  --dir ~/Music/歌单 \
  --webhook "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
```

---

<h2 id="mode-2-data-scraping">模式 2: 数据抓取模式</h2>

数据抓取模式**不依赖 go-music-dl Docker**，直接从平台页面或 API 抓取歌曲/歌单的元数据，无需下载音频文件。

### 单曲抓取支持

| 平台 | 链接格式 | 支持 |
|------|---------|:----:|
| **汽水音乐** | `qishui.douyin.com` | ✅ |
| **网易云音乐** | `music.163.com/song?id=xxx` | ✅ |
| **QQ 音乐** | `y.qq.com/n/ryqq/songDetail/xxx` | ✅ |
| **酷狗音乐** | `m.kugou.com/share/song.html?chain=xxx` | ✅ 新增 |

**使用示例**：
```bash
# 酷狗单曲
python3 music_toolkit.py music-detail "https://m.kugou.com/share/song.html?chain=303ppc3G1V2"

# 网易云单曲
python3 music_toolkit.py music-detail "https://music.163.com/song?id=xxx"

# QQ音乐单曲
python3 music_toolkit.py music-detail "https://y.qq.com/n/ryqq/songDetail/xxx"
```

### 歌单抓取支持

| 平台 | 歌单来源格式 | 曲目列表 | 评论数 | 收藏数 | 分享数 | 发布日期 |
|------|------------|:-------:|:-----:|:-----:|:-----:|:-------:|
| **汽水音乐** | `qishui.douyin.com` 分享链接 | ✅ 全量 | ✅ | ✅ | ✅ | ✅ |
| **网易云音乐** | `music.163.com/playlist?id=xxx` | ✅ 全量 | ✅ 批量 | ❌ | ❌ | ✅ |
| **QQ 音乐** | `y.qq.com` / `c6.y.qq.com` 短链 | ✅ 全量 | ❌ | ❌ | ❌ | ✅ |
| **酷狗音乐** | `t1.kugou.com` 短链 / `wwwapi.kugou.com/share/zlist.html` | ✅ 全量 | ❌ | ❌ | ❌ | ❌ |
| **酷狗音乐** | `kugou.com/songlist/gcid_xxx/` 直链 (需 KuGouMusicApi) | ✅ 全量 | ❌ | ❌ | ❌ | ✅ 部分 |

> **汽水最全**：SSR 渲染，一次 GET 拿到全部数据；网易云有批量评论 API；QQ 和酷狗互动统计不对外开放。

#### 酷狗音乐特色功能

**完整歌单支持**：
- ✅ **KuGouMusicApi 集成**：突破 SSR 10 首限制，获取完整歌单
- ✅ **智能回退**：API 不可用时自动使用网页抓取
- ✅ **多种格式**：支持 `gcid_xxx`、短链 `t1.kugou.com`、`zlist.html` 等格式
- ✅ **单曲分享**：支持 `m.kugou.com/share/song.html` 单曲链接抓取

**链接格式**：
- 歌单短链：`https://t1.kugou.com/xxx`
- 歌单直链：`https://www.kugou.com/songlist/gcid_xxx/`
- zlist 格式：`http://wwwapi.kugou.com/share/zlist.html?...`
- 单曲分享：`https://m.kugou.com/share/song.html?chain=xxx`

**歌曲链接**：
- 生成可直接打开的分享链接：`https://www.kugou.com/song/#hash={歌曲hash}`
- 不再使用搜索链接，确保链接可用性

### 场景 A: 多平台多歌单混合抓取（重磅功能）🔥

**一条命令抓取多个平台的多个歌单，输出统一格式的 CSV 表格**，支持酷狗、汽水、QQ音乐、网易云任意组合。

```bash
# 基础用法：传入多个歌单链接（空格分隔）
python3 music_toolkit.py multi-playlist \
  "https://t1.kugou.com/311Fhf2G1V2" \
  "https://qishui.douyin.com/s/ixTvrn76/" \
  "https://i2.y.qq.com/n3/other/pages/details/playlist.html?id=9475333126" \
  "https://163cn.tv/6IUPicb"

# 指定输出文件名
python3 music_toolkit.py multi-playlist \
  "歌单链接1" "歌单链接2" "歌单链接3" \
  --output my_playlist.csv
```

**输出示例**：

```
🎵 开始多平台多歌单混合抓取...

1. 抓取: https://t1.kugou.com/311Fhf2G1V2...
   ✅ [酷狗] 次次_灏.Hao_高音质在线试听... (44 首)
2. 抓取: https://qishui.douyin.com/s/ixTvrn76/...
   ✅ [汽水] 爱喽叽歪（AI音乐探索者）喜欢的音乐... (49 首)
3. 抓取: https://i2.y.qq.com/n3/other/pages/details/playlist.html...
   ✅ [QQ音乐] 我喜欢... (14 首)
4. 抓取: https://163cn.tv/6IUPicb...
   ✅ [网易云] 盗版... (5 首)

📊 汇总统计:
   总歌单数: 4
   总歌曲数: 112

✅ 已导出到: multi_platform_playlist.csv
```

**CSV 表格结构（15 列统一格式）**：

| 列名 | 说明 | 示例 |
|------|------|------|
| 序号 | 全局序号 | 1, 2, 3... |
| 歌单名称 | 来源歌单标题 | 次次_灏.Hao_高音质在线试听 |
| 歌单平台 | 歌单所属平台（中文） | 酷狗、汽水、QQ音乐、网易云 |
| 歌曲名 | 歌曲标题 | 次次 |
| 歌手 | 演唱者 | 灏.Hao |
| 歌曲链接 | 可直接打开的链接 | https://www.kugou.com/song/#hash=xxx |
| 时长(秒) | 歌曲时长 | 187 |
| 专辑 | 所属专辑 | - |
| 发布日期 | 发布时间 | 2024-01-01 |
| 平台 | 歌曲平台（中文） | 酷狗、汽水、QQ音乐、网易云 |
| 歌曲ID | 平台内部ID | A9AAA9D912C95DA0F67D6EB38924AC84 |
| 收藏数 | 收藏/点赞数 | 1234 |
| 评论数 | 评论数量 | 567 |
| 分享数 | 分享次数 | 89 |
| 播放数 | 播放次数 | 12345 |

**特点**：
- ✅ **跨平台统一**：所有平台使用相同的 15 列表头
- ✅ **来源追溯**：每首歌都标记来自哪个歌单、哪个平台
- ✅ **可直接打开**：歌曲链接可直接在浏览器打开播放
- ✅ **Excel 友好**：UTF-8 BOM 编码，Excel 可直接打开
- ✅ **数据完整**：保留各平台特有数据（汽水音乐统计最全）

**使用场景**：
- 🎯 收集多个平台的喜欢歌单，合并分析
- 🎯 对比不同平台同一歌曲的数据表现
- 🎯 批量导出歌单用于数据分析或备份
- 🎯 AI Agent 自动化处理多源音乐数据

### 场景 B: 查看单个歌单数据（终端输出）

### 场景 B: 查看单个歌单数据（终端输出）

```bash
# 汽水音乐（全量统计数据）
python3 music_toolkit.py playlist-detail "https://qishui.douyin.com/s/ixrkNUQa/"

# 网易云（含评论数 + 发布日期）
python3 music_toolkit.py playlist-detail "https://music.163.com/playlist?id=17662978875"

# QQ 音乐（含专辑 + 发布日期）
python3 music_toolkit.py playlist-detail "https://c6.y.qq.com/base/fcgi-bin/u?__=yJqRiy5AM0uy"

# 酷狗音乐（多种格式支持）
python3 music_toolkit.py playlist-detail "https://t1.kugou.com/2ZNMP4eG1V2"  # 短链 → 全量
python3 music_toolkit.py playlist-detail "https://www.kugou.com/songlist/gcid_xxx/"  # 直链 → 全量（需 KuGouMusicApi）
python3 music_toolkit.py playlist-detail "http://wwwapi.kugou.com/share/zlist.html?..."  # zlist 格式 → 全量

# 酷狗单曲（新增支持）
python3 music_toolkit.py music-detail "https://m.kugou.com/share/song.html?chain=303ppc3G1V2"

# JSON 输出（含完整曲目数组，方便程序处理）
python3 music_toolkit.py playlist-detail "https://qishui.douyin.com/s/ixrkNUQa/" --json
```

### 场景 C: 生成飞书多维表格（`playlist-to-table`）

一条命令完成：抓取歌单 → 创建飞书在线多维表格，**汽水 / 网易云 / QQ / 酷狗通用**。

```bash
# 基础用法（不需要 --sort，直接建表）
python3 music_toolkit.py playlist-to-table "https://qishui.douyin.com/s/ixrkNUQa/"
python3 music_toolkit.py playlist-to-table "https://music.163.com/playlist?id=17662978875"
python3 music_toolkit.py playlist-to-table "https://c6.y.qq.com/base/fcgi-bin/u?__=yJqRiy5AM0uy"
python3 music_toolkit.py playlist-to-table "https://t1.kugou.com/2jaCZcaG1V2"

# 按点赞降序排列
python3 music_toolkit.py playlist-to-table "<url>" --sort likes

# 建表后向飞书群发送含链接的卡片
python3 music_toolkit.py playlist-to-table "<url>" --sort likes --chat-id oc_xxx
```

**多维表格字段（13 列，各平台统一结构）**：

| 列 | 说明 | 汽水 | 网易云 | QQ | 酷狗 |
|----|------|:---:|:-----:|:--:|:---:|
| 序号 | 排序后的行号 | ✅ | ✅ | ✅ | ✅ |
| 平台 | 数据来源平台名 | ✅ | ✅ | ✅ | ✅ |
| song_id | 平台内部歌曲 ID | ✅ | ✅ | ✅ | hash |
| 歌名 | 歌曲标题 | ✅ | ✅ | ✅ | ✅ |
| 歌手 | 演唱艺人 | ✅ | ✅ | ✅ | ✅ |
| 时长 | MM:SS 格式 | ✅ | ✅ | ✅ | ✅ |
| 专辑 | 所属专辑名 | ✅ | ✅ | ✅ | ❌ |
| 发布日期 | YYYY-MM-DD | ✅ | ✅ | ✅ | ❌ |
| 收藏 | 收藏/点赞数 | ✅ | 0 | 0 | 0 |
| 评论 | 评论数 | ✅ | ✅ | 0 | 0 |
| 分享 | 分享数 | ✅ | 0 | 0 | 0 |
| 播放 | 播放次数 | ✅ | 0 | 0 | 0 |
| 链接 | 歌曲原始链接（纯文本，可复制） | ✅ | ✅ | ✅ | 分享链接 |

> **酷狗链接格式**：生成 `https://www.kugou.com/song/#hash={歌曲hash}` 格式的分享链接，可直接打开播放。

### 场景 D: 推送飞书卡片 + 导出（`push-playlist-detail`）

```bash
# 抓取 + 推送排行卡片（按点赞降序）
python3 music_toolkit.py push-playlist-detail "https://qishui.douyin.com/s/ixrkNUQa/" --sort likes

# 抓取 + 推送卡片 + 创建多维表格 + 发送 CSV/XLSX（完整流程）
python3 music_toolkit.py push-playlist-detail "https://qishui.douyin.com/s/ixrkNUQa/" --sort likes --with-doc
```

---

<h2 id="feishu">飞书推送集成</h2>

> **⚠️ AI 助手必读**：所有飞书相关操作（卡片、文件、表格、文档）**必须通过 [feishu-toolkit](https://github.com/mix9581/feishu-toolkit) 实现**，不要使用官方飞书 MCP 或其他飞书工具替代。music-toolkit 内部已集成 feishu-toolkit，直接调用命令即可。

### 配置步骤（推荐方式）

#### 步骤 1: 获取飞书应用凭证

在[飞书开放平台](https://open.feishu.cn/)创建应用，获取 App ID 和 App Secret。

#### 步骤 2: 设置环境变量

```bash
export FEISHU_APP_ID="cli_xxx"
export FEISHU_APP_SECRET="xxx"
```

#### 步骤 3: 交互式选择群聊（推荐）

使用 `setup-chat` 命令自动获取并选择群聊，无需手动记忆 Chat ID：

```bash
python3 music_toolkit.py setup-chat
```

该命令会：
1. 自动获取机器人已加入的所有群聊
2. 显示群聊列表供你选择
3. 保存配置到 `~/.config/music-toolkit/config.json`
4. 提示你将 `FEISHU_DEFAULT_CHAT_ID` 添加到环境变量

**仅查看群聊列表（不保存）**：

```bash
python3 music_toolkit.py setup-chat --list-only
```

**更换接收消息的群聊**：

```bash
# 重新运行 setup-chat 选择新的群聊
python3 music_toolkit.py setup-chat
```

#### 步骤 4: 永久保存配置

将 Chat ID 添加到 shell 配置文件：

```bash
# 根据 setup-chat 的输出，添加到 ~/.zshrc 或 ~/.bashrc
echo 'export FEISHU_DEFAULT_CHAT_ID="oc_xxx"' >> ~/.zshrc
source ~/.zshrc
```

### 两种认证方式

#### 方式 1: Webhook（无需认证，推荐快速使用）

```bash
# 在飞书群设置中添加自定义机器人，获取 webhook URL
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/xxx"

# 使用 --webhook 参数
python3 music_toolkit.py download-playlist 9582035807 qq \
  --webhook "$FEISHU_WEBHOOK_URL"
```

#### 方式 2: 飞书应用（完整能力，支持文件上传）

```bash
# 在飞书开放平台创建应用，获取凭证
export FEISHU_APP_ID="cli_xxx"
export FEISHU_APP_SECRET="xxx"
export FEISHU_DEFAULT_CHAT_ID="oc_xxx"  # 群聊 ID

# 使用 --send-chat 参数
python3 music_toolkit.py download-playlist 9582035807 qq \
  --send-chat "$FEISHU_DEFAULT_CHAT_ID" \
  --lyrics-doc
```

### 文件上传策略（自动处理）

| 文件大小 | 上传方式 | 实现 |
|---------|---------|------|
| ≤ 30MB | IM 直接发送 | `feishu-toolkit` 的 `send_file()` |
| > 30MB | 云盘分片上传 | `feishu-toolkit` 的 `upload_large_file()` + 分片逻辑 |

**分片上传流程**（自动处理，无需手动调用）:

```python
# music-toolkit 内部调用 feishu-toolkit 的能力
from feishu_toolkit import upload_large_file, send_card

# 1. 分片上传到飞书云盘
file_token = upload_large_file(zip_path, chunk_size=4*1024*1024)

# 2. 设置分享权限
set_file_permission(file_token, "organization")

# 3. 发送下载卡片
send_card(chat_id, {
    "title": "🎵 歌单下载完成",
    "content": f"文件大小: {file_size_mb} MB",
    "link": f"https://xxx.feishu.cn/file/{file_token}"
})
```

### 数据抓取卡片示例

使用 `feishu-toolkit` 的富文本卡片能力：

```python
# music-toolkit 内部实现
from feishu_toolkit import send_interactive_card

card_data = {
    "header": {"title": "📊 歌单数据报告"},
    "elements": [
        {"tag": "div", "text": f"**歌单名称**: {playlist_name}"},
        {"tag": "div", "text": f"**平台**: {platform}"},
        {"tag": "div", "text": f"**歌曲数量**: {song_count} 首"},
        {"tag": "hr"},
        {"tag": "markdown", "content": top_songs_table},
        {"tag": "action", "actions": [
            {"tag": "button", "text": "查看完整数据", "url": csv_url}
        ]}
    ]
}

send_interactive_card(chat_id, card_data)
```

---

<h2 id="api">API 参考</h2>

### CLI 命令速查

#### 搜索命令

```bash
# 搜索歌曲（跨平台）
python3 music_toolkit.py search "晴天"
python3 music_toolkit.py search "晴天" --source qq --source netease
python3 music_toolkit.py search "晴天" --json

# 搜索歌单
python3 music_toolkit.py search-playlist "周杰伦精选"
python3 music_toolkit.py search-playlist "周杰伦" --source netease
```

#### 下载命令

```bash
# 下载单曲
python3 music_toolkit.py download <song_id> <source>
python3 music_toolkit.py download <song_id> <source> --name "晴天" --artist "周杰伦" --dir ~/Music

# 下载歌单
python3 music_toolkit.py download-playlist <playlist_id> <source> --dir ~/Music

# 下载单曲并发送到飞书
python3 music_toolkit.py download-send <song_id> <source> --name "歌名" --artist "歌手"
```

#### 数据抓取命令

```bash
# 单曲详情（汽水/网易云/QQ）
python3 music_toolkit.py music-detail "<share_url>"
python3 music_toolkit.py music-detail "<share_url>" --lyrics --json

# 批量单曲详情
python3 music_toolkit.py music-detail-batch "<url1>" "<url2>"
python3 music_toolkit.py music-detail-batch --file urls.txt --delay 2.0

# 歌单详情（汽水/网易云/QQ/酷狗）
python3 music_toolkit.py playlist-detail "<share_url>"
python3 music_toolkit.py playlist-detail "<share_url>" --json
python3 music_toolkit.py playlist-detail "<share_url>" --lyrics --dir ./lyrics

# 歌单 → 飞书多维表格（四平台通用）
python3 music_toolkit.py playlist-to-table "<share_url>"
python3 music_toolkit.py playlist-to-table "<share_url>" --sort likes --chat-id oc_xxx

# 歌单 → 飞书卡片推送
python3 music_toolkit.py push-playlist-detail "<share_url>" --sort likes
python3 music_toolkit.py push-playlist-detail "<share_url>" --sort likes --with-doc
```

#### 飞书推送命令

```bash
# 配置飞书群聊（交互式选择）
python3 music_toolkit.py setup-chat
python3 music_toolkit.py setup-chat --list-only  # 仅列出群聊

# Webhook 推送
python3 music_toolkit.py push-webhook "晴天" <webhook_url>
python3 music_toolkit.py parse-url <music_url> --webhook <webhook_url>

# App API 推送
python3 music_toolkit.py push-song <song_id> <source>
python3 music_toolkit.py push-search "晴天"
python3 music_toolkit.py push-playlist <playlist_id> <source>
python3 music_toolkit.py send-to-chat ~/Music/*.mp3
```

### Python API 示例

```python
from music_toolkit import MusicClient, FeishuPusher

# 初始化客户端
client = MusicClient()
pusher = FeishuPusher()

# 搜索歌曲
results = client.search("晴天", sources=["qq", "netease"])

# 获取歌单
songs = client.get_playlist_songs("9582035807", "qq")

# 下载歌曲
client.download_song(song_id, source, output_dir="~/Music")

# 抓取数据
data = client.scrape_playlist("9582035807", "qq")

# 推送到飞书
pusher.send_card(chat_id, card_data)
pusher.create_playlist_lyrics_doc(songs, title="歌词文档")
```

---

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

# 酷狗歌单（无需 cookie：仅前 10 首 + 歌单基本信息）
python3 music_toolkit.py playlist-detail "https://m.kugou.com/songlist/gcid_xxx/"

# 同时下载每首歌的歌词文件（.lrc + .txt）
python3 music_toolkit.py playlist-detail "https://qishui.douyin.com/s/ixrkNUQa/" \
  --lyrics --dir ~/Downloads/lyrics

# 输出 JSON（含完整曲目数组）
python3 music_toolkit.py playlist-detail "https://qishui.douyin.com/s/ixrkNUQa/" --json

# 抓取后直接推送到飞书群（需配置 App 环境变量）
python3 music_toolkit.py push-playlist-detail "https://qishui.douyin.com/s/ixrkNUQa/"
```

### 歌单数据抓取 + 飞书推送 + 导出（完整流程）

一条命令完成：抓取歌单 → 推送排行卡片到飞书群 → 创建在线表格 → 发送 CSV + XLSX 文件。

**第 1 步：准备环境（仅首次）**

```bash
# 安装依赖
pip install requests openpyxl

# 配置飞书凭证（推送到飞书群时需要）
export FEISHU_APP_ID="cli_xxx"
export FEISHU_APP_SECRET="xxx"
export FEISHU_DEFAULT_CHAT_ID="oc_xxx"

# 确认 feishu-toolkit 在同级目录
ls ../feishu-toolkit/feishu_toolkit.py
```

**第 2 步：执行命令**

```bash
# 仅抓取数据（终端输出，不需要飞书）
python3 music_toolkit.py playlist-detail "https://qishui.douyin.com/s/ixhJKBKw/"

# 抓取 + 推送卡片到飞书群（按点赞降序排列）
python3 music_toolkit.py push-playlist-detail "https://qishui.douyin.com/s/ixhJKBKw/" --sort likes

# 抓取 + 推送卡片 + 导出在线表格/CSV/XLSX（完整流程）
python3 music_toolkit.py push-playlist-detail "https://qishui.douyin.com/s/ixhJKBKw/" --sort likes --with-doc
```

**第 3 步：飞书群收到的内容**

使用 `--with-doc` 后，飞书群会依次收到 4 条消息：

```
                        push-playlist-detail --sort likes --with-doc
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         ▼                          ▼                          ▼
  ① 歌单排行卡片              ② CSV + XLSX 文件           ③ 在线表格卡片
  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
  │ w.               │     │ w._20260401_     │     │ w. — 完整数据     │
  │ 创建者 · 120 首  │     │   071002.csv     │     │                  │
  │ ─────────────── │     │ w._20260401_     │     │ 共 120 首曲目数据 │
  │ 歌曲名    收藏.. │     │   071002.xlsx    │     │ 已导出            │
  │ 1.心若止水 67.1万 │     │                  │     │ [打开在线表格]    │
  │ 2.回溯原点 56.9万 │     │ 点击下载即可     │     │                  │
  │ ...120首...      │     └──────────────────┘     └──────────────────┘
  │ 数据来源: Soda   │
  │ 排序: 点赞 降序  │
  └──────────────────┘
```

**三种导出格式对比**

| 格式 | 用途 | 数字格式 | 需要 |
|------|------|---------|------|
| **飞书在线表格** | 团队协作，在线排序筛选 | 原始数字 | 飞书凭证 |
| **CSV** | 万能格式，任何工具可打开 | 文本（防科学计数法） | 飞书凭证 |
| **XLSX** | 本地 Excel，有表头样式 | 原始数字 + 冻结首行 | 飞书凭证 + openpyxl |

**执行链路（AI 必读）**

```
python3 music_toolkit.py push-playlist-detail "<url>" --sort likes --with-doc
    │
    ├── music_toolkit.py                     ← 本项目
    │   ├── get_playlist_detail_from_url()   ← 纯 HTTP 抓取，无需 LLM
    │   ├── FeishuPusher.push_playlist_detail_card()
    │   │   └── 构建卡片 JSON → send_card()
    │   └── FeishuPusher._send_playlist_csv()
    │       ├── create_bitable_with_fields() → 在线表格
    │       ├── csv.writer() → CSV 文件
    │       └── openpyxl.Workbook() → XLSX 文件
    │
    └── ../feishu-toolkit/feishu_toolkit.py  ← 依赖项目
        ├── FeishuClient.create_bitable_with_fields()  ← 创建在线表格 + 定义列
        ├── FeishuClient.create_bitable_records()      ← 批量写入数据
        ├── FeishuClient.upload_file()                 ← 上传 CSV/XLSX
        ├── FeishuClient.send_file()                   ← 发送文件到群
        └── FeishuClient.send_card()                   ← 发送卡片消息
```

#### 各平台数据能力对比

不同平台的公开 API 开放程度差异很大，直接决定了能抓到的数据粒度：

**不需要 cookie（当前实现）**

| 数据项 | 汽水音乐 | 网易云 | QQ音乐 | 酷狗 |
|--------|:--------:|:------:|:------:|:----:|
| 歌单基本信息 | ✅ | ✅ | ✅ | ✅ |
| 曲目列表（全部） | ✅ | ✅ | ✅ | ✅ 短链全量 / ⚠️ gcid 直链仅前 10 首 |
| 单曲评论数 | ✅ | ✅ 批量 API | ❌ | ❌ |
| 单曲收藏数 | ✅ | ❌ | ❌ | ❌ |
| 单曲分享数 | ✅ | ❌ | ❌ | ❌ |
| 发布日期 | ✅ | ✅ | ✅ | ❌ |

**配合 cookie 后（展望）**

| 数据项 | 汽水音乐 | 网易云 | QQ音乐 | 酷狗 |
|--------|:--------:|:------:|:------:|:----:|
| 曲目列表（全部） | ✅ 已满 | ✅ 已满 | ✅ 已满 | ✅ 可获取全部 |
| 单曲评论数 | ✅ 已满 | ✅ 已满 | ⚠️ 有接口但需签名 | ❌ 平台不开放 |
| 单曲收藏/分享 | ✅ 已满 | ❌ 平台不开放 | ❌ 平台不开放 | ❌ 平台不开放 |

**技术本质差异**

| 平台 | 架构 | 为什么汽水最好抓 |
|------|------|----------------|
| 汽水音乐 | SSR，数据内嵌 `_ROUTER_DATA` | 服务端渲染，一次 GET 全拿，收藏/评论/分享全开放 |
| 网易云 | SPA，数据异步加载 | 有 `/api/batch` 可批量拿评论数，收藏/分享不开放 |
| QQ 音乐 | SPA，数据异步加载 | 旧版 fcg API 返回曲目列表，统计数据被封 |
| 酷狗 | SPA + 强签名保护 | `gcid_xxx` 直链 SSR 仅前 10 首；`t1.kugou.com` 短链 → `zlist.html` 可全量（无需 cookie） |

**酷狗歌单全量抓取（无需 cookie）**

酷狗提供两种分享链接，数据获取方式不同：

| 链接格式 | 示例 | 全量获取 | 说明 |
|---------|------|:-------:|------|
| `t1.kugou.com/xxx` 短链 | `https://t1.kugou.com/2jaCZcaG1V2` | ✅ | 重定向到 `zlist.html`，全部曲目内嵌在 JS 变量里 |
| `wwwapi.kugou.com/share/zlist.html?...` | 浏览器地址栏完整 URL | ✅ | 直接解析，支持两种内嵌格式 |
| `kugou.com/songlist/gcid_xxx/` 直链 | `https://www.kugou.com/songlist/gcid_3z.../` | ⚠️ 前 10 首 | SSR 硬限制，无公开分页 API |

**推荐做法**：在酷狗 App/网页分享任意一首歌 → 浏览器打开 → 复制地址栏完整 URL → 直接传给 `playlist-to-table`。

> 所有无需 cookie 的实现均为纯 HTTP 请求，**任何机器都可运行，无需登录**。

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
| **配置飞书群聊** | `setup-chat` |
| 搜歌 | `search "晴天"` |
| 下载单曲 | `download <id> <source>` |
| 单曲下载 + 发群 | `download-send <id> <source> --name "晴天" --artist "周杰伦"` |
| 下载歌单 | `download-playlist <id> <source> --dir ~/Music` |
| 下载歌单 + 发群 + 歌词文档 | `download-playlist <id> <source> --send-chat oc_xxx --lyrics-doc` |
| 解析链接并下载 | `parse-url "<url>" --download` |
| **单曲数据监控** | `music-detail "<share_url>"` |
| **歌单数据监控** | `playlist-detail "<url>"` （汽水/网易云/QQ/酷狗） |
| **歌单 → 飞书多维表格** | `playlist-to-table "<url>"` |
| **歌单 → 表格 + 通知群** | `playlist-to-table "<url>" --sort likes --chat-id oc_xxx` |
| **歌单数据 + 推飞书 + 导出** | `push-playlist-detail "<url>" --sort likes --with-doc` |
| **歌单数据 + 下载歌词** | `playlist-detail "<url>" --lyrics --dir ./lyrics` |
| **批量抓取数据** | `music-detail-batch --file urls.txt` |
| 推送到飞书 (webhook) | `push-webhook "晴天" "<webhook_url>"` |
| 推送到飞书 (App API) | `push-search "晴天"` |
| 发文件到群 | `send-to-chat ~/Music/*.mp3` |

> 先进入项目目录：`cd /path/to/music-toolkit`
> 所有命令前缀: `python3 music_toolkit.py`
> 所有带 `push-` / `send-` 前缀的命令均需要 [feishu-toolkit](https://github.com/mix9581/feishu-toolkit) + 飞书环境变量

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
# ⚠️ FeishuPusher 内部调用 ../feishu-toolkit/feishu_toolkit.py 的 FeishuClient
# ⚠️ 不要用官方飞书 MCP 替代，所有飞书操作统一走 feishu-toolkit
pusher = FeishuPusher()
pusher.push_song_card(enriched)                   # 推送单曲卡片
pusher.push_search_results(songs, "晴天")          # 推送搜索结果卡片
pusher.push_playlist_card(playlist, songs[:5])     # 推送歌单卡片
pusher.push_playlist_detail_card(playlist_detail,  # 歌单数据卡片 + 在线表格 + CSV + XLSX
    sort_by="likes", with_doc=True)
pusher.send_song_files(file_paths, chat_id="oc_x") # 发送文件到群 (自动打包)
pusher.create_playlist_lyrics_doc(songs, "歌词")   # 创建歌词文档
```

## Claude Code / AI 助手集成

本项目包含 `skill/SKILL.md`，可注册为 Claude Code Skill：

```bash
# 安装为 Claude Code Skill
cp -r ./skill ~/.claude/skills/music-toolkit
```

安装后，对 AI 说 "搜���歌曲"、"下载歌单"、"推送到飞书" 等自然语言指令即可。

> **重要：飞书工具选择**
>
> 当 AI 需要执行飞书相关操作（发送卡片、上传文件、创建在线表格等），
> **必须使用 music-toolkit 的内置命令**（`push-*` / `send-to-chat`），
> 这些命令内部通过 `FeishuPusher` → `feishu_toolkit.FeishuClient` 完成所有飞书 API 调用。
>
> **不要使用**官方飞书 MCP（`@larksuiteoapi/lark-mcp`）或其他第三方飞书工具替代，
> 它们不支持本项目的卡片样式、在线表格创建、文件打包上传等定制功能。

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `GO_MUSIC_DL_URL` | go-music-dl 服务地址 | `http://localhost:8080` |
| `DOWNLOAD_DIR` | 下载保存目录 | `./downloads` |
| `FEISHU_APP_ID` | 飞书应用 ID | (App API 推送时需要) |
| `FEISHU_APP_SECRET` | 飞书应用 Secret | (App API 推送时需要) |
| `FEISHU_DEFAULT_CHAT_ID` | 默认飞书群 ID | (App API 推送时需要，建议用 `setup-chat` 配置) |

> **推荐配置方式**：使用 `python3 music_toolkit.py setup-chat` 交互式选择群聊，自动获取 Chat ID，无需手动记忆。
>
> Webhook 推送不需要环境变量，只需提供 webhook URL。

## 测试

```bash
pip install pytest
python3 -m pytest tests/ -v
```

## 实测验证

以下示例均经过真实环境验证（2026-03-30 / 2026-04-01）：

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
python3 music_toolkit.py download-playlist 9582035807 qq \
  --dir ~/Music/qq --send-chat oc_xxx --lyrics-doc

python3 music_toolkit.py download-playlist 17662978875 netease \
  --dir ~/Music/netease --send-chat oc_xxx --lyrics-doc

python3 music_toolkit.py download-playlist 7602191490944712731 soda \
  --dir ~/Music/soda --send-chat oc_xxx --lyrics-doc
```

每首歌下载 3 个文件：`.mp3` + `.lrc`（带时间轴）+ `.txt`（纯文本）。zip 打包后通过飞书云盘分片上传，群内收到 1 条卡片消息 + 1 条歌词文档链接。

### Flow C: 歌单数据监控 + 飞书卡片 + 数据导出（v0.3.x）

| 平台 | 歌单 | 曲目 | 评论数 | 收藏/分享 | 导出 |
|------|------|------|--------|-----------|------|
| 汽水音乐 | [w.](https://qishui.douyin.com/s/ixhJKBKw/) | 120 首全部 | ✅ | ✅ | 在线表格 + CSV + XLSX |
| 汽水音乐 | [阿勋](https://qishui.douyin.com/s/ixhe6brH/) | 185 首全部 | ✅ | ✅ | 在线表格 + CSV + XLSX |
| 网易云 | [陶喆精选](https://music.163.com/playlist?id=17662978875) | 15 首全部 | ✅ 批量 | ❌ | 同上 |
| QQ音乐 | [何玄歌单](https://y.qq.com/n/ryqq_v2/playlist/9582035807) | 25 首全部 | ❌ | ❌ | 同上 |
| 酷狗 | [lgy — 每日推荐](https://m.kugou.com/songlist/gcid_3zvpukfkz4z092/) | 10/30 首 | ❌ | ❌ | 同上 |

```bash
# 汽水 120首 — 卡片 + 在线表格 + CSV + XLSX 一步到位
python3 music_toolkit.py push-playlist-detail "https://qishui.douyin.com/s/ixhJKBKw/" --sort likes --with-doc

# 网易云 — 含评论数，按评论降序
python3 music_toolkit.py push-playlist-detail "https://music.163.com/playlist?id=17662978875" --sort comments --with-doc

# QQ 音乐 — 按日期升序
python3 music_toolkit.py push-playlist-detail "https://y.qq.com/n/ryqq_v2/playlist/9582035807" --sort date --asc --with-doc
```

### `--with-doc` 完整数据导出

卡片受飞书 30KB 上限影响，超长歌单的统计数字会被缩写（如 `67.1万`）。加 `--with-doc` 会在推送卡片后额外发一个 CSV 文件到同群，包含**所有曲目原始数据**：

```
#, song_id, 歌名, 歌手, 时长, 专辑, 发布日期, 收藏, 评论, 分享, 播放, 链接
1, 7617026170865223721, 心若止水, w., 3:42, ..., 2025-07-15, 670997, 3468, 32069, 0, https://...
```

- `song_id` 即汽水音乐的 `track_id`，可用于后续单曲详情抓取
- CSV 使用 UTF-8 BOM 编码（Excel 直接打开中文不乱码）
- 不受卡片显示条数限制，185 首全量导出

---

<h2 id="card-tech">歌单卡片技术方案与踩坑记录</h2>

> **AI 助手必读**：本节记录了 `push-playlist-detail` 的完整技术路径、飞书卡片的限制、以及每个平台的数据获取难点。若你需要修改卡片推送逻辑或新增平台，请先阅读本节。

### 整体架构

```
用户提供歌单分享链接
    │
    ▼
playlist-detail（纯 Python，无需 LLM，无需 go-music-dl）
    │  HTTP GET → 解析页面/API → PlaylistDetailInfo
    ▼
push-playlist-detail（需要 feishu-toolkit）
    │  构建飞书卡片 JSON → send_card()
    │  可选：生成 CSV → upload_file() → send_file()
    ▼
飞书群收到：① 卡片消息  ② CSV 文件（--with-doc）
```

**关键依赖链**：`push-playlist-detail` → `FeishuPusher` → 动态导入 `../feishu-toolkit/feishu_toolkit.py` → `FeishuClient.send_card()` / `send_file()`。如果 AI 需要发送卡片，**必须使用 music-toolkit 的 push-* 命令**，不要直接调用 feishu-toolkit 或官方 MCP。

### 飞书卡片限制与对策

| 限制 | 具体值 | 影响 | 对策 |
|------|--------|------|------|
| **卡片 JSON 大小** | ~30KB | 超限返回 400 Bad Request | 见下方卡片瘦身方案 |
| **card_column_set 行数** | 无官方限制 | 但每行一个 column_set 会 JSON 爆炸 | 不使用每行一个 column_set |
| **markdown 文本长度** | 无官方限制 | 单个 card_markdown 块可放数百行 | 长歌单放在一个块内 |

**卡片瘦身演进路径**（实测数据，120 首歌单）：

| 方案 | JSON 大小 | 支持曲目数 | 对齐效果 |
|------|----------|-----------|---------|
| 每行一个 card_column_set (4列) | 78 KB ❌ | ~30 首 | 完美对齐 |
| 每行一个 card_column_set (2列) | 49 KB ❌ | ~50 首 | 完美对齐 |
| 单个 card_markdown 文本块 | 13 KB ✅ | 200+ 首 | ❌ 数字不对齐 |
| **单个 card_column_set + 2列 markdown** | **15 KB ✅** | **200+ 首** | **✅ 左右列对齐** |

最终方案：一个 `card_column_set` 包含两个 `card_column`，每列内部是一个 `card_markdown` 块，用 `\n` 分隔每首歌。左列放歌名（weight=6），右列放统计数字（weight=4），行数自动对齐。

### 各平台数据获取难点

#### 汽水音乐（最佳，完整数据）

- **技术**：SSR 页面，`_ROUTER_DATA` 变量包含全部数据
- **数据**：收藏/评论/分享/播放、歌词、音频直链、发布日期、曲风全开放
- **限制**：无。185 首一次 GET 全拿，无需翻页
- **song_id**：`track_id` 字段，同时也是 `resolved_url` 里的 `track_id=xxx`

#### 网易云音乐（含评论数）

- **技术**：SPA 架构，需调 2 个 API
  1. `/api/v6/playlist/detail` — 歌单信息 + 前 ~10 首曲目 + `trackIds[]` 全量 ID 列表
  2. `/api/song/detail` — 补齐 `trackIds[]` 中缺失的曲目
  3. `/api/batch` — **批量**获取每首歌评论数（一个 POST 请求搞定所有）
- **难点**：v6 API 只返回前 ~10 首的完整 `tracks[]`，需要用 `trackIds[]` 二次查询
- **限制**：收藏/分享数平台不开放（公开 API 不返回，即使有 cookie 也拿不到）

#### QQ 音乐（基础信息）

- **技术**：旧版 `fcg_ucc_getcdinfo_byids_cp.fcg` API（无需签名，稳定可用）
- **数据**：歌名、歌手、时长、专辑、发布日期、封面
- **难点**：新版 musics.fcg API 需要签名，旧版不需要但没有统计数据
- **限制**：评论数 API 已封锁（返回 0），收藏/分享数平台不开放

#### 酷狗音乐（前 10 首）

- **技术**：PC 页面 SSR `window.$output` 变量（需随机 X-Forwarded-For 绕过限速）
- **难点**：
  - 签名密钥 `NVPh5oo715z5DIWAeQlhMDsWXXQV4hwt` 已知，但 gcid 格式歌单的 `specialid=0`，无法调用 `mobilecdn` 翻页 API
  - `window.$output` 固定只嵌入前 10 首，与登录状态无关
  - 加 cookie 后 `window.$output` 依然只有 10 首（服务端 SSR 硬限制）
- **限制**：完整曲目需要通过签名 API + cookie，当前未实现

### 开发踩坑记录

1. **飞书卡片 400 错误**：120 首歌用每行一个 `card_column_set`（4 列）生成 78KB JSON，直接 400。飞书没有在文档中明确写上限，实测约 30KB。

2. **分批 column_set 有割裂感**：把 50 首一批放进一个 column_set 可以控制大小，但视觉上每 50 首有一个断裂。最终改为全部行放进一个 column_set 的两个 markdown 块。

3. **酷狗 X-Forwarded-For**：不加随机 IP header 时 `window.$output` 不返回数据（空页面），go-music-dl 源码中的 `WithRandomIPHeader()` 是关键。

4. **网易云 v6 API 曲目不全**：`/api/v6/playlist/detail?n=1000` 声称支持 1000 首，实际只返回 ~10 首的完整 `tracks[]`，但 `trackIds[]` 包含全部。需要对比两者差集后二次请求。

5. **网易云 batch 评论 API**：逐首查询评论数太慢（每首一个 HTTP 请求），发现 `/api/batch` 可以在一个 POST 请求中批量查询多首歌的评论数，15 首只需 0.8 秒。

6. **CSV 编码**：普通 UTF-8 的 CSV 用 Excel 打开中文乱码，改用 `utf-8-sig`（带 BOM）后自动识别。

7. **数字格式**：飞书 markdown 里数字 `670,997` 占位太宽，改用万为单位 `67.1万`，既省空间又直观。CSV 保留原始数字。

## License

MIT
