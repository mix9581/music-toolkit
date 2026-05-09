# KuGouMusicApi 集成说明

## 概述

music-toolkit 已集成 [KuGouMusicApi](https://github.com/MakcRe/KuGouMusicApi)，用于获取酷狗音乐完整歌单数据。

## 问题背景

默认情况下，酷狗歌单抓取受限于：
- **SSR 限制**：网页抓取最多返回 10 首歌曲
- **反爬限制**：需要随机 IP header 绕过限速
- **不稳定**：依赖页面结构，容易失效

## 解决方案

通过集成 KuGouMusicApi Node.js 服务：
- ✅ **完整数据**：突破 SSR 限制，获取歌单所有歌曲
- ✅ **无需 Cookie**：公开歌单直接访问
- ✅ **稳定可靠**：基于官方 API 封装
- ✅ **自动回退**：API 不可用时使用网页抓取

## 快速开始

### 方式 1: Docker Compose（推荐）

```bash
# 启动服务
docker-compose -f docker-compose.kugou-api.yml up -d

# 验证服务
curl http://localhost:3000/

# 使用（无需额外配置）
python3 music_toolkit.py playlist-detail "https://www.kugou.com/songlist/gcid_xxx/"
```

### 方式 2: 手动启动

```bash
# 克隆项目
git clone https://github.com/MakcRe/KuGouMusicApi.git
cd KuGouMusicApi

# 安装依赖
npm install

# 启动服务
npm run dev

# 验证
curl http://localhost:3000/playlist/detail?ids=collection_3_1863870844_4_0
```

### 方式 3: 自定义端口

```bash
# 修改端口
export KUGOU_API_URL="http://localhost:4000"

# 启动服务（自定义端口）
PORT=4000 npm run dev

# 使用
python3 music_toolkit.py playlist-detail "https://www.kugou.com/songlist/gcid_xxx/"
```

## 工作原理

### 自动检测与回退

```python
# music_toolkit.py 内部逻辑
def _scrape_kugou_playlist_detail(share_url: str):
    # 1. 提取 gcid
    gcid = extract_gcid(share_url)
    
    # 2. 尝试使用 KuGouMusicApi（优先）
    try:
        api_url = os.environ.get("KUGOU_API_URL", "http://localhost:3000")
        return fetch_via_api(api_url, gcid)
    except:
        # 3. 回退到网页抓取（最多 10 首）
        return scrape_from_web(share_url)
```

### 对用户透明

无需修改任何命令，自动选择最佳方式：

```bash
# 相同的命令
python3 music_toolkit.py playlist-detail "https://www.kugou.com/songlist/gcid_xxx/"

# KuGouMusicApi 可用 → 获取完整歌单（100+ 首）
# KuGouMusicApi 不可用 → 网页抓取（最多 10 首）
```

## API 接口说明

### 1. 歌单详情

```bash
GET /playlist/detail?ids=collection_3_1863870844_4_0
```

返回：
- 歌单标题、创建者、封面
- 播放量、收藏量、评论数
- 歌单简介

### 2. 歌单所有歌曲

```bash
GET /playlist/track/all?id=collection_3_1863870844_4_0&page=1&pagesize=100
```

返回：
- 歌曲列表（支持分页）
- 歌曲名、歌手、时长
- 歌曲 hash（用于下载）

## 测试

### 代码验证（无需服务）

```bash
python3 test_kugou_integration.py
```

验证内容：
- 代码导入和语法
- 函数签名
- 回退逻辑
- gcid 格式转换

### 完整测试（需要服务）

```bash
# 启动服务
docker-compose -f docker-compose.kugou-api.yml up -d

# 运行测试
python3 test_kugou_api.py
```

测试内容：
- 服务健康检查
- 歌单详情接口
- 歌单歌曲列表接口
- music_toolkit 集成

## 故障排查

### 问题 1: 服务无法启动

```bash
# 检查端口占用
lsof -i :3000

# 更换端口
PORT=4000 npm run dev
export KUGOU_API_URL="http://localhost:4000"
```

### 问题 2: API 返回错误

```bash
# 检查服务日志
docker-compose -f docker-compose.kugou-api.yml logs -f

# 重启服务
docker-compose -f docker-compose.kugou-api.yml restart
```

### 问题 3: 回退到网页抓取

原因：
- KuGouMusicApi 服务未启动
- 网络连接问题
- API 返回错误

解决：
```bash
# 检查服务状态
curl http://localhost:3000/

# 查看 music_toolkit 日志（会显示回退原因）
python3 music_toolkit.py playlist-detail "https://www.kugou.com/songlist/gcid_xxx/" -v
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `KUGOU_API_URL` | `http://localhost:3000` | KuGouMusicApi 服务地址 |

## 性能对比

| 方式 | 歌曲数量 | 速度 | 稳定性 |
|------|----------|------|--------|
| 网页抓取 | 最多 10 首 | 慢（需随机 IP） | 低（易被限速） |
| KuGouMusicApi | 完整歌单 | 快（官方 API） | 高（稳定接口） |

## 相关资源

- [KuGouMusicApi GitHub](https://github.com/MakcRe/KuGouMusicApi)
- [KuGouMusicApi 文档](https://github.com/MakcRe/KuGouMusicApi/blob/main/docs/README.md)
- [music-toolkit 主文档](README.md)

## 贡献

欢迎提交 Issue 和 PR：
- 报告 Bug
- 功能建议
- 文档改进
