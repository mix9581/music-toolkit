# go-music-dl API Reference

go-music-dl 是一个自部署的音乐聚合搜索与下载服务，通过 Docker 运行在 localhost:8080。

## 基础信息

- **Base URL**: `http://localhost:8080`
- **所有路径前缀**: `/music/`
- **搜索返回**: HTML（需要解析 `data-*` 属性）
- **其他接口**: JSON 或文件流

## API Endpoints

### 1. 搜索歌曲

```
GET /music/search?q={keyword}&sources={sources}&type=song
```

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| q | string | 搜索关键词 |
| sources | string | 逗号分隔的平台代码 (可选) |
| type | string | `song` (默认) 或 `playlist` |

**返回**: HTML 页面，歌曲数据在 `<li class="song-card">` 的 data 属性中：

```html
<li class="song-card"
    data-id="0042rlGx2WHBrG"
    data-source="qq"
    data-duration="278"
    data-name="晴天 (深情版)"
    data-artist="Lucky小爱"
    data-cover="https://y.gtimg.cn/music/photo_new/..."
    data-extra='{"songmid":"0042rlGx2WHBrG"}'>
```

### 2. 搜索歌单

```
GET /music/search?q={keyword}&sources={sources}&type=playlist
```

**返回**: HTML 页面，歌单数据在 `<div class="playlist-card">` 中：
- 歌单 ID 和平台在 `onclick` URL 中: `/music/playlist?id=xxx&source=netease`
- 封面: `<img src="...">`
- 标题: `<div class="playlist-title">`
- 创建者: `<div class="playlist-author">`
- 歌曲数: `<div class="playlist-count">共 147 首</div>`

### 3. 获取歌词

```
GET /music/lyric?id={song_id}&source={source}
```

**返回**: LRC 格式纯文本

```
[ti:晴天 (深情版)]
[ar:Lucky小爱]
[00:30.42]故事的小黄花
[00:33.97]从出生那年就飘着
...
```

### 4. 检查歌曲资源 (Inspect)

```
GET /music/inspect?id={song_id}&source={source}&duration={duration}
```

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| id | string | 歌曲 ID |
| source | string | 平台代码 |
| duration | int | 时长（秒，可选） |

**返回**: JSON
```json
{
  "valid": true,
  "url": "https://ws.stream.qqmusic.qq.com/...",
  "size": "4.3 MB",
  "bitrate": "-"
}
```

### 5. 换源搜索

```
GET /music/switch_source?name={name}&artist={artist}&source={source}&duration={duration}
```

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| name | string | 歌曲名 |
| artist | string | 歌手名 |
| source | string | 当前平台（排除，可选） |
| duration | int | 时长（秒，可选） |

**返回**: JSON
```json
{
  "id": "bLnv0PqDX_qAlIqapc+Okw==",
  "source": "joox",
  "name": "晴天",
  "artist": "周杰倫",
  "duration": 269,
  "cover": "https://image.joox.com/...",
  "album": "葉惠美",
  "link": "https://www.joox.com/...",
  "score": 0.9
}
```

### 6. 下载歌曲

```
GET /music/download?id={song_id}&source={source}&name={name}&artist={artist}&cover={cover}&embed={embed}&extra={extra}
```

**返回**: 音频文件流 (MP3)
- Content-Disposition 头包含文件名

### 7. 下载歌词文件

```
GET /music/download_lrc?id={song_id}&source={source}&name={name}&artist={artist}
```

**返回**: LRC 文件

### 8. 下载封面

```
GET /music/download_cover?url={cover_url}&name={name}&artist={artist}
```

**返回**: 图片文件流

### 9. 歌单详情

```
GET /music/playlist?id={playlist_id}&source={source}
```

**返回**: HTML 页面，与搜索结果格式相同，包含 `<li class="song-card">` 歌曲列表。

## 支持的平台代码

| 代码 | 名称 | 备注 |
|------|------|------|
| netease | 网易云音乐 | |
| qq | QQ音乐 | |
| kugou | 酷狗音乐 | |
| kuwo | 酷我音乐 | |
| migu | 咪咕音乐 | |
| qianqian | 千千音乐 | |
| soda | Soda音乐 | |
| fivesing | 5sing | |
| jamendo | Jamendo (CC) | 免费版权音乐 |
| joox | JOOX | |
| bilibili | 哔哩哔哩 | |

## 注意事项

1. 搜索接口返回 HTML，需要通过正则解析 `data-*` 属性
2. `inspect` 和 `switch_source` 返回 JSON
3. `lyric` 返回纯文本 (LRC 格式)
4. `download` 相关接口返回文件流
5. 平台可用性可能因 Cookie 配置而异
6. 某些平台需要登录 Cookie 才能获取高音质资源
