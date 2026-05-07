# Cookie 管理指南

## 为什么需要 Cookie？

部分音乐平台的内容需要登录态才能访问：

| 平台 | 需要 Cookie 的场景 |
|------|-------------------|
| **网易云音乐** | 会员专享歌曲、付费歌曲、完整歌单 |
| **QQ音乐** | 会员歌曲、无损音质、完整歌单 |
| **酷狗音乐** | 完整歌单（默认只返回前10首）、会员歌曲 |
| **酷我音乐** | 会员歌曲、高品质音频 |
| **咪咕音乐** | 部分独家内容 |
| **哔哩哔哩** | 部分音频内容 |

---

## 快速开始

### 1. 获取 Cookie

#### 方法 A: 浏览器开发者工具（推荐）

以网易云音乐为例：

1. 打开 https://music.163.com 并登录
2. 按 `F12` 打开开发者工具
3. 切换到 **Network** (网络) 标签
4. 刷新页面 (`F5`)
5. 点击任意请求（如 `api/xxx`）
6. 在右侧找到 **Request Headers** (请求头)
7. 找到 `Cookie:` 字段，复制完整内容

**示例 Cookie**:
```
MUSIC_U=abc123def456; __csrf=xyz789; ...
```

#### 方法 B: 浏览器插件

使用 Cookie 导出插件（如 EditThisCookie、Cookie-Editor）：
1. 安装插件
2. 访问音乐平台并登录
3. 点击插件图标
4. 导出 Cookie（选择 Netscape 或 JSON 格式）

---

### 2. 设置 Cookie

#### 方式 1: 命令行设置（推荐）

```bash
# 设置网易云 Cookie
python3 music_toolkit.py cookie set netease "MUSIC_U=abc123def456; __csrf=xyz789"

# 设置 QQ 音乐 Cookie
python3 music_toolkit.py cookie set qq "uin=123456; qm_keyst=xxx; psrf_qqopenid=xxx"

# 设置酷狗 Cookie
python3 music_toolkit.py cookie set kugou "kg_mid=xxx; kg_dfid=xxx"
```

#### 方式 2: 环境变量

```bash
# 添加到 ~/.bashrc 或 ~/.zshrc
export NETEASE_COOKIE="MUSIC_U=abc123def456"
export QQ_MUSIC_COOKIE="uin=123456; qm_keyst=xxx"
export KUGOU_COOKIE="kg_mid=xxx"

# 重新加载配置
source ~/.zshrc

# 加载到 go-music-dl
python3 music_toolkit.py cookie load --env
```

#### 方式 3: JSON 文件

创建 `.music_cookies.json`:

```json
{
  "netease": "MUSIC_U=abc123def456; __csrf=xyz789",
  "qq": "uin=123456; qm_keyst=xxx; psrf_qqopenid=xxx",
  "kugou": "kg_mid=xxx; kg_dfid=xxx",
  "kuwo": "Hm_token=xxx",
  "migu": "aversionid=xxx",
  "bilibili": "SESSDATA=xxx; bili_jct=xxx"
}
```

加载 Cookie:

```bash
python3 music_toolkit.py cookie load --file .music_cookies.json
```

---

## 常用命令

### 查看当前 Cookie

```bash
python3 music_toolkit.py cookie list
```

**输出示例**:
```
🍪 当前 Cookie 配置:

  netease      (网易云音乐)
               MUSIC_U=abc123def456; __csrf=xyz789...
  qq           (QQ音乐)
               uin=123456; qm_keyst=xxx; psrf_qqopenid=...
  kugou        (酷狗音乐)
               kg_mid=xxx; kg_dfid=xxx...

  共 3 个平台
```

### 更新 Cookie

```bash
# 直接覆盖即可
python3 music_toolkit.py cookie set netease "NEW_COOKIE_VALUE"
```

### 删除 Cookie

```bash
# 删除单个平台
python3 music_toolkit.py cookie delete netease

# 删除多个平台
python3 music_toolkit.py cookie delete netease qq kugou

# 清除所有
python3 music_toolkit.py cookie clear
```

### 备份和恢复

```bash
# 备份当前 Cookie
python3 music_toolkit.py cookie save --file backup_$(date +%Y%m%d).json

# 恢复 Cookie
python3 music_toolkit.py cookie load --file backup_20260408.json
```

---

## 平台特定说明

### 网易云音乐 (netease)

**关键 Cookie 字段**:
- `MUSIC_U` - 用户身份标识（最重要）
- `__csrf` - CSRF 令牌

**获取方式**:
1. 登录 https://music.163.com
2. 开发者工具 → Network → 任意 API 请求
3. 复制完整 Cookie

**有效期**: 通常 30 天，过期后需重新获取

### QQ 音乐 (qq)

**关键 Cookie 字段**:
- `uin` - 用户 QQ 号
- `qm_keyst` - 登录密钥
- `psrf_qqopenid` - OpenID

**获取方式**:
1. 登录 https://y.qq.com
2. 开发者工具 → Network → 任意请求
3. 复制完整 Cookie

**有效期**: 通常 7-30 天

### 酷狗音乐 (kugou)

**关键 Cookie 字段**:
- `kg_mid` - 设备标识
- `kg_dfid` - 设备指纹

**获取方式**:
1. 登录 https://www.kugou.com
2. 开发者工具 → Network
3. 复制完整 Cookie

**特别说明**:
- 酷狗歌单默认只返回前 10 首（SSR 限制）
- 设置 Cookie 后可获取完整歌单

### 酷我音乐 (kuwo)

**关键 Cookie 字段**:
- `Hm_token` - 用户令牌

**获取方式**:
1. 登录 http://www.kuwo.cn
2. 开发者工具 → Network
3. 复制完整 Cookie

### 咪咕音乐 (migu)

**关键 Cookie 字段**:
- `aversionid` - 版本标识

**获取方式**:
1. 登录 https://music.migu.cn
2. 开发者工具 → Network
3. 复制完整 Cookie

### 哔哩哔哩 (bilibili)

**关键 Cookie 字段**:
- `SESSDATA` - 会话数据（最重要）
- `bili_jct` - CSRF 令牌

**获取方式**:
1. 登录 https://www.bilibili.com
2. 开发者工具 → Network
3. 复制完整 Cookie

**有效期**: 通常 30 天

---

## 使用场景

### 场景 1: 下载网易云会员歌曲

```bash
# 1. 设置 Cookie
python3 music_toolkit.py cookie set netease "MUSIC_U=xxx"

# 2. 搜索歌曲
python3 music_toolkit.py search "周杰伦 晴天" --source netease

# 3. 下载（会员歌曲现在可以访问了）
python3 music_toolkit.py download SONG_ID netease
```

### 场景 2: 获取酷狗完整歌单

```bash
# 1. 设置 Cookie
python3 music_toolkit.py cookie set kugou "kg_mid=xxx; kg_dfid=xxx"

# 2. 下载歌单（现在可以获取全部歌曲，不再限制 10 首）
python3 music_toolkit.py download-playlist PLAYLIST_ID kugou --dir ~/Music
```

### 场景 3: 批量设置多个平台

```bash
# 创建 JSON 文件
cat > .music_cookies.json << 'EOF'
{
  "netease": "MUSIC_U=xxx",
  "qq": "uin=xxx; qm_keyst=xxx",
  "kugou": "kg_mid=xxx"
}
EOF

# 一次性加载
python3 music_toolkit.py cookie load

# 验证
python3 music_toolkit.py cookie list
```

### 场景 4: CI/CD 环境

```bash
# GitHub Actions / GitLab CI
export NETEASE_COOKIE="${{ secrets.NETEASE_COOKIE }}"
export QQ_MUSIC_COOKIE="${{ secrets.QQ_MUSIC_COOKIE }}"

python3 music_toolkit.py cookie load --env
python3 music_toolkit.py download-playlist PLAYLIST_ID netease
```

---

## 安全建议

### ⚠️ Cookie 是敏感信息

Cookie 包含你的登录凭证，泄露后他人可以：
- 访问你的账号
- 查看你的收藏和歌单
- 使用你的会员权益

### 🔒 安全实践

1. **不要提交到 Git**:
   ```bash
   # 添加到 .gitignore
   echo ".music_cookies.json" >> .gitignore
   echo "*.cookie" >> .gitignore
   ```

2. **使用环境变量**:
   ```bash
   # 不要硬编码在脚本中
   export NETEASE_COOKIE="xxx"  # ✅ 好

   # 避免
   cookie="xxx"  # ❌ 不好
   ```

3. **定期更新**:
   - Cookie 有有效期（通常 7-30 天）
   - 过期后需重新获取
   - 建议每月更新一次

4. **最小权限原则**:
   - 只设置需要的平台
   - 不需要时及时删除

5. **使用专用账号**:
   - 建议使用测试账号的 Cookie
   - 避免使用主账号

---

## 故障排查

### Cookie 无效？

**症状**: 设置 Cookie 后仍然无法访问会员内容

**解决方案**:
1. 检查 Cookie 是否完整（包含所有字段）
2. 检查 Cookie 是否过期（重新登录获取）
3. 检查平台是否更新了验证机制
4. 尝试清除后重新设置

```bash
# 清除并重新设置
python3 music_toolkit.py cookie delete netease
python3 music_toolkit.py cookie set netease "NEW_COOKIE"
```

### Cookie 过期？

**症状**: 之前可用的 Cookie 突然失效

**解决方案**:
1. 重新登录音乐平台
2. 获取新的 Cookie
3. 更新配置

```bash
python3 music_toolkit.py cookie set netease "NEW_COOKIE"
```

### 如何验证 Cookie 是否生效？

```bash
# 1. 查看当前配置
python3 music_toolkit.py cookie list

# 2. 尝试搜索/下载
python3 music_toolkit.py search "测试歌曲" --source netease

# 3. 查看 go-music-dl 日志
docker logs go-music-dl
```

---

## 技术原理

### Cookie 存储位置

Cookie 保存在 go-music-dl 的数据库中：
- **容器内路径**: `/app/data/cookies.json`
- **持久化**: 通过 Docker volume 持久化
- **格式**: SQLite 数据库

### API 调用流程

```
music-toolkit
    │
    │ POST /cookies
    │ {"netease": "MUSIC_U=xxx"}
    ▼
go-music-dl (Docker)
    │
    │ 保存到数据库
    │ data/cookies.json
    ▼
music-lib (Go)
    │
    │ 搜索/下载时自动附加 Cookie
    ▼
音乐平台 API
```

### Cookie 管理器

go-music-dl 内置 `CookieManager`:
- 线程安全（使用 `sync.RWMutex`）
- 自动加载和保存
- 支持多平台

---

## 常见问题

### Q: Cookie 会过期吗？

**A**: 会的。不同平台有效期不同：
- 网易云: 约 30 天
- QQ音乐: 约 7-30 天
- 酷狗: 约 30 天

过期后需重新获取。

### Q: 可以同时设置多个账号的 Cookie 吗？

**A**: 不可以。每个平台只能设置一个 Cookie。如需切换账号，需要重新设置。

### Q: Cookie 会被其他人看到吗？

**A**:
- 本地使用：只有你能访问
- Docker 容器：只在容器内部
- 网络传输：通过 localhost，不会暴露到公网

### Q: 忘记设置了哪些 Cookie？

**A**: 使用 `cookie list` 查看：
```bash
python3 music_toolkit.py cookie list
```

### Q: 如何批量导入 Cookie？

**A**: 使用 JSON 文件：
```bash
python3 music_toolkit.py cookie load --file cookies.json
```

---

## 更新日志

- **2026-04-08**: 初始版本，支持 6 个平台的 Cookie 管理
- 支持命令行、环境变量、JSON 文件三种方式
- 集成到 go-music-dl 的 Cookie 管理系统

---

## 相关链接

- [music-toolkit README](./README.md)
- [go-music-dl 项目](https://github.com/guohuiyuan/go-music-dl)
- [feishu-toolkit 项目](https://github.com/mix9581/feishu-toolkit)
