#!/usr/bin/env python3
"""
Music Toolkit — 音乐搜索/下载/飞书推送工具包。

封装 go-music-dl HTTP API，提供搜索、歌词、下载、飞书卡片推送等功能。
设计理念: 单文件 + CLI + 可 import，配合 SKILL.md 让 AI 一看就会用。

用法 - 作为模块:
    from music_toolkit import MusicClient
    client = MusicClient()
    songs = client.search_songs("晴天")

用法 - 作为 CLI:
    python music_toolkit.py search "晴天"
    python music_toolkit.py search "晴天" --source qq --source netease
    python music_toolkit.py lyrics 0042rlGx2WHBrG qq
    python music_toolkit.py detail 0042rlGx2WHBrG qq
    python music_toolkit.py download 0042rlGx2WHBrG qq
    python music_toolkit.py platforms

依赖: requests (pip install requests)
"""

import os
import re
import sys
import json
import html
import argparse
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

try:
    import requests
except ImportError:
    print("Error: 'requests' package required. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

__version__ = "0.1.0"

# ─── Constants ────────────────────────────────────────────────────────────────

DEFAULT_BASE_URL = "http://localhost:8080"
DEFAULT_DOWNLOAD_DIR = "./downloads"

PLATFORMS = {
    "netease": "网易云音乐",
    "qq": "QQ音乐",
    "kugou": "酷狗音乐",
    "kuwo": "酷我音乐",
    "migu": "咪咕音乐",
    "qianqian": "千千音乐",
    "soda": "Soda音乐",
    "fivesing": "5sing",
    "jamendo": "Jamendo (CC)",
    "joox": "JOOX",
    "bilibili": "哔哩哔哩",
}

ALL_SOURCES = list(PLATFORMS.keys())


# ─── Data Models ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Song:
    """歌曲数据模型"""
    id: str
    source: str
    name: str
    artist: str
    duration: int
    cover: str
    album: str = ""
    lyrics: str = ""
    url: str = ""
    size: str = ""
    bitrate: str = ""
    link: str = ""
    score: float = 0.0
    extra: dict = field(default_factory=dict)

    @property
    def duration_str(self) -> str:
        """格式化时长 (e.g. 4:29)"""
        if self.duration <= 0:
            return "0:00"
        minutes = self.duration // 60
        seconds = self.duration % 60
        return f"{minutes}:{seconds:02d}"

    @property
    def source_name(self) -> str:
        """平台中文名"""
        return PLATFORMS.get(self.source, self.source)

    def to_dict(self) -> dict:
        """转为字典（含计算属性）"""
        result = asdict(self)
        result["duration_str"] = self.duration_str
        result["source_name"] = self.source_name
        return result


@dataclass(frozen=True)
class Playlist:
    """歌单数据模型"""
    id: str
    source: str
    name: str
    cover: str
    track_count: int = 0
    play_count: int = 0
    creator: str = ""
    description: str = ""

    @property
    def source_name(self) -> str:
        return PLATFORMS.get(self.source, self.source)

    def to_dict(self) -> dict:
        result = asdict(self)
        result["source_name"] = self.source_name
        return result


@dataclass(frozen=True)
class InspectResult:
    """歌曲资源检查结果"""
    valid: bool
    url: str
    size: str
    bitrate: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DownloadResult:
    """单首歌曲下载结果"""
    song: Song
    success: bool
    filepath: Optional[Path] = None
    lrc_path: Optional[Path] = None
    actual_source: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        d = {
            "name": self.song.name,
            "artist": self.song.artist,
            "source": self.song.source,
            "actual_source": self.actual_source or self.song.source,
            "success": self.success,
        }
        if self.filepath:
            d["filepath"] = str(self.filepath)
        if self.lrc_path:
            d["lrc_path"] = str(self.lrc_path)
        if self.error:
            d["error"] = self.error
        return d


# ─── HTML Parsing Helpers ─────────────────────────────────────────────────────

def _parse_song_cards(html_text: str) -> list[Song]:
    """从 go-music-dl 搜索结果 HTML 中解析歌曲列表。

    HTML 结构:
      <li class="song-card" data-id="xxx" data-source="qq"
          data-duration="278" data-name="晴天" data-artist="周杰伦"
          data-cover="https://..." data-extra='{"songmid":"xxx"}'>
    """
    songs = []
    # Match each song-card <li> block
    card_pattern = re.compile(
        r'<li\s+class="song-card"[^>]*?'
        r'data-id="([^"]*)"[^>]*?'
        r'data-source="([^"]*)"[^>]*?'
        r'data-duration="([^"]*)"[^>]*?'
        r'data-name="([^"]*)"[^>]*?'
        r'data-artist="([^"]*)"[^>]*?'
        r'data-cover="([^"]*)"',
        re.DOTALL,
    )
    extra_pattern = re.compile(r"data-extra='([^']*)'")
    # 专辑名在 artist-line 里: <i ...></i> 歌手名 &nbsp;•&nbsp; 专辑名
    album_pattern = re.compile(
        r'<div\s+class="artist-line">[^<]*<i[^>]*></i>\s*[^&]*&nbsp;•&nbsp;\s*([^<\n]+)',
    )

    for match in card_pattern.finditer(html_text):
        song_id, source, duration_str, name, artist, cover = match.groups()

        # Grab a wider block to extract extra + album
        block_end = min(match.start() + 2000, len(html_text))
        card_html = html_text[match.start():block_end]

        # Try to extract extra JSON data
        extra = {}
        extra_match = extra_pattern.search(card_html)
        if extra_match:
            try:
                extra_raw = html.unescape(extra_match.group(1))
                extra = json.loads(extra_raw)
            except (json.JSONDecodeError, ValueError):
                pass

        # Try to extract album name
        album = ""
        album_match = album_pattern.search(card_html)
        if album_match:
            album = html.unescape(album_match.group(1).strip())

        songs.append(Song(
            id=html.unescape(song_id),
            source=html.unescape(source),
            name=html.unescape(name),
            artist=html.unescape(artist),
            duration=int(duration_str) if duration_str.isdigit() else 0,
            cover=html.unescape(cover),
            album=album,
            extra=extra,
        ))

    return songs


def _parse_playlist_cards(html_text: str) -> list[Playlist]:
    """从 go-music-dl 歌单搜索结果 HTML 中解析歌单列表。

    HTML 结构:
      <div class="playlist-card" onclick="location.href='/music/playlist?id=xxx&source=netease'">
        <div class="playlist-cover"><img src="..." ...></div>
        <div class="playlist-meta">
          <div class="playlist-title">名称</div>
          <div class="playlist-author"><i ...></i> 创建者</div>
          <div class="playlist-count">共 147 首</div>
        </div>
      </div>
    """
    playlists = []

    # Extract each playlist-card block
    card_pattern = re.compile(
        r'<div\s+class="playlist-card"[^>]*onclick="location\.href=\'[^\']*\?id=([^&]*)&(?:amp;)?source=([^\']*)\'"[^>]*>',
        re.DOTALL,
    )
    img_pattern = re.compile(r'<img\s+src="([^"]*)"')
    title_pattern = re.compile(r'<div\s+class="playlist-title">\s*(.*?)(?:\s*<a\s)', re.DOTALL)
    author_pattern = re.compile(r'<div\s+class="playlist-author">[^<]*<i[^>]*></i>\s*([^<]*)</div>')
    count_pattern = re.compile(r'<div\s+class="playlist-count">共\s*(\d+)\s*首</div>')

    # Split HTML by playlist-card blocks
    card_splits = re.split(r'(?=<div\s+class="playlist-card")', html_text)

    for block in card_splits:
        card_match = card_pattern.search(block)
        if not card_match:
            continue

        playlist_id = card_match.group(1)
        source = card_match.group(2)

        img_match = img_pattern.search(block)
        cover = img_match.group(1) if img_match else ""

        title_match = title_pattern.search(block)
        name = title_match.group(1).strip() if title_match else ""
        # Clean HTML entities and whitespace
        name = html.unescape(re.sub(r'\s+', ' ', name).strip())

        author_match = author_pattern.search(block)
        creator = author_match.group(1).strip() if author_match else ""

        count_match = count_pattern.search(block)
        track_count = int(count_match.group(1)) if count_match else 0

        playlists.append(Playlist(
            id=playlist_id,
            source=source,
            name=name,
            cover=cover,
            track_count=track_count,
            creator=creator,
        ))

    return playlists


# ─── MusicClient: go-music-dl HTTP Client ─────────────────────────────────────

class MusicClientError(Exception):
    """MusicClient 业务异常"""
    pass


class MusicClient:
    """go-music-dl HTTP API 客户端。

    Args:
        base_url: go-music-dl 服务地址 (默认 http://localhost:8080)
        timeout: HTTP 请求超时秒数
    """

    def __init__(
        self,
        base_url: str = None,
        timeout: int = 30,
    ):
        raw_url = base_url or os.environ.get("GO_MUSIC_DL_URL", DEFAULT_BASE_URL)
        self.base_url = raw_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()

    # ── Search ─────────────────────────────────────────────────────────────

    def search_songs(
        self,
        keyword: str,
        sources: list[str] = None,
    ) -> list[Song]:
        """搜索歌曲。

        Args:
            keyword: 搜索关键词
            sources: 搜索平台列表 (默认全部)

        Returns:
            歌曲列表
        """
        params = {"q": keyword, "type": "song"}
        if sources:
            params["sources"] = ",".join(sources)
        resp = self._get("/music/search", params=params)
        return _parse_song_cards(resp.text)

    def search_playlists(
        self,
        keyword: str,
        sources: list[str] = None,
    ) -> list[Playlist]:
        """搜索歌单。

        Args:
            keyword: 搜索关键词
            sources: 搜索平台列表 (默认全部)

        Returns:
            歌单列表
        """
        params = {"q": keyword, "type": "playlist"}
        if sources:
            params["sources"] = ",".join(sources)
        resp = self._get("/music/search", params=params)
        return _parse_playlist_cards(resp.text)

    # ── Song Details ───────────────────────────────────────────────────────

    def get_lyrics(self, song_id: str, source: str) -> str:
        """获取歌词 (LRC 格式文本)。

        Args:
            song_id: 歌曲 ID
            source: 音源平台

        Returns:
            LRC 格式歌词文本
        """
        resp = self._get("/music/lyric", params={"id": song_id, "source": source})
        return resp.text.strip()

    def inspect(
        self,
        song_id: str,
        source: str,
        duration: int = 0,
    ) -> InspectResult:
        """检查歌曲资源详情 (URL/大小/码率)。

        Args:
            song_id: 歌曲 ID
            source: 音源平台
            duration: 歌曲时长（秒），用于更精确的匹配

        Returns:
            InspectResult 包含 valid, url, size, bitrate
        """
        params = {"id": song_id, "source": source}
        if duration > 0:
            params["duration"] = str(duration)
        resp = self._get("/music/inspect", params=params)
        data = resp.json()
        return InspectResult(
            valid=data.get("valid", False),
            url=data.get("url", ""),
            size=data.get("size", ""),
            bitrate=data.get("bitrate", ""),
        )

    def switch_source(
        self,
        name: str,
        artist: str,
        source: str = "",
        duration: int = 0,
    ) -> Optional[Song]:
        """换源搜索 - 在其他平台查找相同歌曲。

        Args:
            name: 歌曲名
            artist: 歌手名
            source: 当前平台 (排除该平台)
            duration: 歌曲时长

        Returns:
            找到的 Song 或 None
        """
        params = {
            "name": name,
            "artist": artist,
        }
        if source:
            params["source"] = source
        if duration > 0:
            params["duration"] = str(duration)
        resp = self._get("/music/switch_source", params=params)
        if resp.status_code != 200:
            return None
        try:
            data = resp.json()
        except (json.JSONDecodeError, ValueError):
            return None

        return Song(
            id=data.get("id", ""),
            source=data.get("source", ""),
            name=data.get("name", ""),
            artist=data.get("artist", ""),
            duration=data.get("duration", 0),
            cover=data.get("cover", ""),
            album=data.get("album", ""),
            link=data.get("link", ""),
            score=data.get("score", 0.0),
        )

    # ── Download ───────────────────────────────────────────────────────────

    def download(
        self,
        song_id: str,
        source: str,
        name: str = "",
        artist: str = "",
        cover: str = "",
        embed: bool = False,
        extra: dict = None,
        save_dir: str = None,
    ) -> Path:
        """下载歌曲音频文件。

        Args:
            song_id: 歌曲 ID
            source: 音源平台
            name: 歌曲名 (用于文件名)
            artist: 歌手名 (用于文件名)
            cover: 封面 URL (embed=True 时嵌入)
            embed: 是否嵌入封面到音频文件
            extra: 额外参数 (JSON dict, go-music-dl 内部使用)
            save_dir: 保存目录

        Returns:
            保存的文件路径
        """
        target_dir = Path(save_dir or os.environ.get("DOWNLOAD_DIR", DEFAULT_DOWNLOAD_DIR))
        target_dir.mkdir(parents=True, exist_ok=True)

        params = {
            "id": song_id,
            "source": source,
        }
        if name:
            params["name"] = name
        if artist:
            params["artist"] = artist
        if cover:
            params["cover"] = cover
        if embed:
            params["embed"] = "true"
        if extra:
            params["extra"] = json.dumps(extra, ensure_ascii=False)

        resp = self._get("/music/download", params=params, stream=True)

        # Determine filename from Content-Disposition or construct one
        filename = _extract_filename(resp) or _build_filename(name, artist, "mp3")
        filepath = target_dir / _sanitize_filename(filename)

        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return filepath

    def download_lyrics_file(
        self,
        song_id: str,
        source: str,
        name: str = "",
        artist: str = "",
        save_dir: str = None,
    ) -> Path:
        """下载歌词文件 (.lrc)。

        Args:
            song_id: 歌曲 ID
            source: 音源平台
            name: 歌曲名
            artist: 歌手名
            save_dir: 保存目录

        Returns:
            保存的歌词文件路径
        """
        target_dir = Path(save_dir or os.environ.get("DOWNLOAD_DIR", DEFAULT_DOWNLOAD_DIR))
        target_dir.mkdir(parents=True, exist_ok=True)

        params = {"id": song_id, "source": source}
        if name:
            params["name"] = name
        if artist:
            params["artist"] = artist

        resp = self._get("/music/download_lrc", params=params)

        filename = _extract_filename(resp) or _build_filename(name, artist, "lrc")
        filepath = target_dir / _sanitize_filename(filename)
        filepath.write_text(resp.text, encoding="utf-8")
        return filepath

    def download_cover(
        self,
        cover_url: str,
        name: str = "",
        artist: str = "",
        save_dir: str = None,
    ) -> Path:
        """下载封面图片。

        Args:
            cover_url: 封面图片 URL
            name: 歌曲名
            artist: 歌手名
            save_dir: 保存目录

        Returns:
            保存的封面文件路径
        """
        target_dir = Path(save_dir or os.environ.get("DOWNLOAD_DIR", DEFAULT_DOWNLOAD_DIR))
        target_dir.mkdir(parents=True, exist_ok=True)

        params = {"url": cover_url}
        if name:
            params["name"] = name
        if artist:
            params["artist"] = artist

        resp = self._get("/music/download_cover", params=params, stream=True)

        filename = _extract_filename(resp) or _build_filename(name, artist, "jpg")
        filepath = target_dir / _sanitize_filename(filename)

        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return filepath

    # ── Playlist ───────────────────────────────────────────────────────────

    def get_playlist_songs(self, playlist_id: str, source: str) -> list[Song]:
        """获取歌单中的所有歌曲。

        Args:
            playlist_id: 歌单 ID
            source: 音源平台

        Returns:
            歌曲列表
        """
        resp = self._get("/music/playlist", params={"id": playlist_id, "source": source})
        return _parse_song_cards(resp.text)

    def download_playlist(
        self,
        playlist_id: str,
        source: str,
        save_dir: str = None,
        on_progress: callable = None,
    ) -> list["DownloadResult"]:
        """批量下载歌单中的所有歌曲（自动换源）。

        逻辑:
          1. 获取歌单歌曲列表
          2. 对每首歌: inspect → 可用则直接下载
          3. 不可用则 switch_source → inspect 换源结果 → 下载
          4. 同时下载歌词文件 (.lrc)

        Args:
            playlist_id: 歌单 ID
            source: 音源平台
            save_dir: 保存目录
            on_progress: 进度回调 fn(index, total, song_name, status_msg)

        Returns:
            每首歌的下载结果列表
        """
        songs = self.get_playlist_songs(playlist_id, source)
        if not songs:
            return []

        results = []
        total = len(songs)

        for idx, song in enumerate(songs, 1):
            if on_progress:
                on_progress(idx, total, song.name, "检查资源...")

            result = self._download_single_with_fallback(song, save_dir=save_dir)

            if on_progress:
                status = "✅" if result.success else f"❌ {result.error}"
                on_progress(idx, total, song.name, status)

            results.append(result)

        return results

    def _download_single_with_fallback(
        self,
        song: Song,
        save_dir: str = None,
    ) -> "DownloadResult":
        """下载单首歌曲，穷尽所有源直到成功。

        策略:
          1. 先尝试原始平台 inspect → 可用则下载
          2. 下载失败 (如 502) → 继续搜其他平台
          3. 原始平台不可用 → 搜索所有平台找匹配 → 逐个尝试
          4. 所有源穷尽仍失败才放弃

        Args:
            song: 歌曲对象
            save_dir: 保存目录

        Returns:
            DownloadResult
        """
        tried_sources = set()
        errors = []

        # ── 尝试 1: 原始平台 ──
        result = self._try_download_from_source(song, song, save_dir)
        if result.success:
            return result
        tried_sources.add(song.source)
        if result.error:
            errors.append(f"{song.source}: {result.error}")

        # ── 尝试 2: switch_source (API 推荐的最佳匹配) ──
        try:
            alt = self.switch_source(
                song.name, song.artist,
                source=song.source, duration=song.duration,
            )
            if alt and alt.id and alt.source not in tried_sources:
                alt_song = Song(
                    id=alt.id, source=alt.source,
                    name=alt.name or song.name,
                    artist=alt.artist or song.artist,
                    duration=alt.duration, cover=alt.cover or song.cover,
                    album=alt.album or song.album,
                    extra=alt.extra,
                )
                result = self._try_download_from_source(song, alt_song, save_dir)
                if result.success:
                    return result
                tried_sources.add(alt.source)
                if result.error:
                    errors.append(f"{alt.source}: {result.error}")
        except Exception:
            pass

        # ── 尝试 3: 全平台搜索，逐个尝试未试过的源 ──
        try:
            search_results = self.search_songs(
                f"{song.name} {song.artist}",
            )
            # 按匹配度排序：名字和歌手都匹配的优先
            candidates = []
            for s in search_results:
                if s.source in tried_sources:
                    continue
                # 简单匹配：歌名包含关系
                name_match = (
                    song.name.lower() in s.name.lower()
                    or s.name.lower() in song.name.lower()
                )
                if name_match:
                    candidates.append(s)

            for candidate in candidates:
                if candidate.source in tried_sources:
                    continue
                result = self._try_download_from_source(song, candidate, save_dir)
                tried_sources.add(candidate.source)
                if result.success:
                    return result
                if result.error:
                    errors.append(f"{candidate.source}: {result.error}")
        except Exception:
            pass

        # ── 全部穷尽 ──
        error_summary = f"已尝试 {len(tried_sources)} 个源均失败"
        if errors:
            # 只显示最后几个错误，避免太长
            last_errors = errors[-3:]
            error_summary += " (" + "; ".join(last_errors) + ")"
        return DownloadResult(
            song=song, success=False,
            actual_source=song.source,
            error=error_summary,
        )

    def _try_download_from_source(
        self,
        original_song: Song,
        download_song: Song,
        save_dir: str = None,
    ) -> "DownloadResult":
        """尝试从指定源下载单首歌曲。

        Args:
            original_song: 原始歌曲（用于文件名和歌词）
            download_song: 实际下载源的歌曲
            save_dir: 保存目录

        Returns:
            DownloadResult (success=True 表示完全成功)
        """
        # inspect 检查
        try:
            inspect_result = self.inspect(
                download_song.id, download_song.source,
                duration=download_song.duration,
            )
        except Exception:
            return DownloadResult(
                song=original_song, success=False,
                actual_source=download_song.source,
                error="inspect 失败",
            )

        if not inspect_result.valid:
            return DownloadResult(
                song=original_song, success=False,
                actual_source=download_song.source,
                error="资源不可用",
            )

        # 下载音频
        try:
            filepath = self.download(
                download_song.id, download_song.source,
                name=original_song.name, artist=original_song.artist,
                cover=download_song.cover, extra=download_song.extra,
                save_dir=save_dir,
            )
        except Exception as e:
            return DownloadResult(
                song=original_song, success=False,
                actual_source=download_song.source,
                error=f"下载失败: {e}",
            )

        # 下载歌词（尽力而为，不影响结果）
        lrc_path = None
        try:
            lrc_path = self.download_lyrics_file(
                original_song.id, original_song.source,
                name=original_song.name, artist=original_song.artist,
                save_dir=save_dir,
            )
        except Exception:
            pass

        return DownloadResult(
            song=original_song, success=True,
            filepath=filepath, lrc_path=lrc_path,
            actual_source=download_song.source,
        )

    # ── Full Detail ────────────────────────────────────────────────────────

    def get_song_full_detail(self, song_id: str, source: str, duration: int = 0) -> Song:
        """获取歌曲完整详情 (inspect + lyrics)。

        组合调用 inspect 和 get_lyrics，返回带完整信息的 Song。

        Args:
            song_id: 歌曲 ID
            source: 音源平台
            duration: 歌曲时长

        Returns:
            带完整信息的 Song（含 url, size, bitrate, lyrics）
        """
        # Get resource info
        inspect_result = self.inspect(song_id, source, duration=duration)

        # Get lyrics
        lyrics = ""
        try:
            lyrics = self.get_lyrics(song_id, source)
        except Exception:
            pass

        return Song(
            id=song_id,
            source=source,
            name="",
            artist="",
            duration=duration,
            cover="",
            url=inspect_result.url,
            size=inspect_result.size,
            bitrate=inspect_result.bitrate,
            lyrics=lyrics,
        )

    def enrich_song(self, song: Song) -> Song:
        """为已有 Song 补充 inspect + lyrics 信息。

        Args:
            song: 基础 Song 对象（来自搜索结果）

        Returns:
            新 Song 对象，补充了 url/size/bitrate/lyrics
        """
        inspect_result = self.inspect(song.id, song.source, duration=song.duration)

        lyrics = ""
        try:
            lyrics = self.get_lyrics(song.id, song.source)
        except Exception:
            pass

        return Song(
            id=song.id,
            source=song.source,
            name=song.name,
            artist=song.artist,
            duration=song.duration,
            cover=song.cover,
            album=song.album,
            link=song.link,
            extra=song.extra,
            url=inspect_result.url,
            size=inspect_result.size,
            bitrate=inspect_result.bitrate,
            lyrics=lyrics,
        )

    # ── Platforms ──────────────────────────────────────────────────────────

    @staticmethod
    def list_platforms() -> dict[str, str]:
        """列出支持的平台。

        Returns:
            {平台代码: 中文名} 字典
        """
        return dict(PLATFORMS)

    # ── Internal HTTP ──────────────────────────────────────────────────────

    def _get(self, path: str, params: dict = None, stream: bool = False) -> requests.Response:
        """发起 GET 请求。"""
        url = f"{self.base_url}{path}"
        try:
            resp = self._session.get(url, params=params, timeout=self.timeout, stream=stream)
            resp.raise_for_status()
            return resp
        except requests.ConnectionError:
            raise MusicClientError(
                f"无法连接到 go-music-dl 服务: {self.base_url}\n"
                "请确保 Docker 容器正在运行。"
            )
        except requests.HTTPError as e:
            raise MusicClientError(f"HTTP 错误: {e}")
        except requests.Timeout:
            raise MusicClientError(f"请求超时 ({self.timeout}s): {url}")


# ─── Filename Helpers ─────────────────────────────────────────────────────────

def _extract_filename(resp: requests.Response) -> str:
    """从 Content-Disposition header 提取文件名。"""
    cd = resp.headers.get("Content-Disposition", "")
    if not cd:
        return ""
    from urllib.parse import unquote
    # Try filename*=UTF-8''... format first (case-insensitive)
    match = re.search(r"filename\*=(?:UTF-8|utf-8)''(.+?)(?:;|$)", cd)
    if match:
        return unquote(match.group(1).strip())
    # Then try filename="..." format
    match = re.search(r'filename="?([^";]+)"?', cd)
    if match:
        return unquote(match.group(1).strip())
    return ""


def _build_filename(name: str, artist: str, ext: str) -> str:
    """构建文件名: 歌名-歌手.ext"""
    if name and artist:
        return f"{name}-{artist}.{ext}"
    if name:
        return f"{name}.{ext}"
    return f"unknown.{ext}"


def _sanitize_filename(filename: str) -> str:
    """清理文件名中的不安全字符。"""
    # Replace unsafe chars with underscore
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename).strip()


# ─── FeishuPusher: Feishu Integration ─────────────────────────────────────────

class FeishuPusher:
    """飞书推送器 — 将音乐数据推送到飞书群。

    依赖 feishu_toolkit.py (~/feishu-toolkit/feishu_toolkit.py)。

    Args:
        app_id: 飞书应用 ID
        app_secret: 飞书应用 Secret
        default_chat_id: 默认推送群组 ID
    """

    def __init__(
        self,
        app_id: str = None,
        app_secret: str = None,
        default_chat_id: str = None,
    ):
        self.default_chat_id = (
            default_chat_id
            or os.environ.get("FEISHU_DEFAULT_CHAT_ID", "")
        )

        # Import feishu_toolkit
        feishu_client_cls = _import_feishu_client()
        self._client = feishu_client_cls(
            app_id=app_id or os.environ.get("FEISHU_APP_ID", ""),
            app_secret=app_secret or os.environ.get("FEISHU_APP_SECRET", ""),
        )

    def _resolve_chat_id(self, chat_id: str = None) -> str:
        """解析 chat_id，优先使用传入值，否则用默认值。"""
        cid = chat_id or self.default_chat_id
        if not cid:
            raise ValueError(
                "chat_id 未指定。请传入 chat_id 参数或设置 FEISHU_DEFAULT_CHAT_ID 环境变量。"
            )
        return cid

    def push_song_card(self, song: Song, chat_id: str = None) -> dict:
        """推送单曲详情卡片到飞书群。

        卡片包含: 歌名、歌手、时长、音质、平台、歌词预览。

        Args:
            song: Song 对象
            chat_id: 目标群组 ID

        Returns:
            飞书 API 响应
        """
        cid = self._resolve_chat_id(chat_id)

        # Build fields
        fields = [
            (f"**歌手**: {song.artist}", True),
            (f"**时长**: {song.duration_str}", True),
        ]
        if song.album:
            fields.append((f"**专辑**: {song.album}", True))
        if song.bitrate:
            fields.append((f"**音质**: {song.bitrate}", True))
        if song.size:
            fields.append((f"**大小**: {song.size}", True))
        fields.append((f"**平台ID**: {song.id}", True))

        elements = [
            self._client.card_fields(fields),
        ]

        # Add lyrics preview if available
        if song.lyrics:
            lyrics_preview = _format_lyrics_preview(song.lyrics, max_lines=4)
            if lyrics_preview:
                elements.append(self._client.card_divider())
                elements.append(self._client.card_markdown(
                    f"📝 **歌词预览**\n{lyrics_preview}"
                ))

        # Source badge in title
        source_emoji = _source_emoji(song.source)
        title = f"🎵 {song.name}    {source_emoji} {song.source_name}"

        card = self._client.build_card(title, elements, color="blue")
        return self._client.send_card(cid, card)

    def push_search_results(
        self,
        songs: list[Song],
        keyword: str,
        chat_id: str = None,
    ) -> dict:
        """推送搜索结果列表卡片到飞书群。

        Args:
            songs: 歌曲列表
            keyword: 搜索关键词
            chat_id: 目标群组 ID

        Returns:
            飞书 API 响应
        """
        cid = self._resolve_chat_id(chat_id)

        lines = []
        for i, song in enumerate(songs[:10], 1):
            line = (
                f"{i}. **{song.name}** - {song.artist} "
                f"({song.duration_str}) [{song.source_name}]"
            )
            if song.size:
                line += f" {song.size}"
            lines.append(line)

        body_text = "\n".join(lines)
        if len(songs) > 10:
            body_text += f"\n\n... 共 {len(songs)} 首"

        elements = [
            self._client.card_markdown(body_text),
        ]

        title = f"🔍 搜索: {keyword} ({len(songs)} 首)"
        card = self._client.build_card(title, elements, color="green")
        return self._client.send_card(cid, card)

    def push_playlist_card(
        self,
        playlist: Playlist,
        songs: list[Song] = None,
        chat_id: str = None,
    ) -> dict:
        """推送歌单卡片到飞书群。

        Args:
            playlist: 歌单对象
            songs: 歌单中的歌曲列表 (可选，显示前 10 首)
            chat_id: 目标群组 ID

        Returns:
            飞书 API 响应
        """
        cid = self._resolve_chat_id(chat_id)

        fields = [
            (f"**创建者**: {playlist.creator}", True),
            (f"**歌曲数**: {playlist.track_count}", True),
            (f"**平台**: {playlist.source_name}", True),
        ]
        if playlist.play_count > 0:
            fields.append((f"**播放量**: {playlist.play_count:,}", True))

        elements = [self._client.card_fields(fields)]

        if playlist.description:
            elements.append(self._client.card_markdown(playlist.description))

        if songs:
            elements.append(self._client.card_divider())
            song_lines = []
            for i, song in enumerate(songs[:10], 1):
                song_lines.append(
                    f"{i}. **{song.name}** - {song.artist} ({song.duration_str})"
                )
            if len(songs) > 10:
                song_lines.append(f"... 共 {len(songs)} 首")
            elements.append(self._client.card_markdown("\n".join(song_lines)))

        title = f"📋 {playlist.name}"
        card = self._client.build_card(title, elements, color="purple")
        return self._client.send_card(cid, card)

    def create_song_document(self, song: Song) -> str:
        """创建飞书文档记录歌曲详情。

        Args:
            song: Song 对象（建议先 enrich）

        Returns:
            文档 URL
        """
        blocks = [
            self._client.heading_block(f"🎵 {song.name}", level=1),
            self._client.text_block(
                f"歌手: {song.artist}  |  时长: {song.duration_str}  |  平台: {song.source_name}"
            ),
            self._client.divider_block(),
        ]

        if song.album:
            blocks.append(self._client.text_block(f"专辑: {song.album}"))
        if song.bitrate:
            blocks.append(self._client.text_block(f"音质: {song.bitrate}  |  大小: {song.size}"))

        if song.lyrics:
            blocks.append(self._client.heading_block("歌词", level=2))
            # Split lyrics into reasonable blocks
            for chunk in _split_lyrics_for_doc(song.lyrics):
                blocks.append(self._client.text_block(chunk))

        result = self._client.create_document_with_content(
            title=f"{song.name} - {song.artist}",
            blocks=blocks,
        )
        return result.get("url", "")

    def send_song_files(
        self,
        file_paths: list[Path],
        chat_id: str = None,
        zip_name: str = "",
    ) -> dict:
        """发送歌曲文件到飞书群。

        逻辑:
          - 1 个文件且 ≤30MB: 直接上传并发送
          - 多个文件: 打包成 zip 后上传发送
          - zip 超 30MB 时: 自动分包 (Part 1, Part 2, ...)

        Args:
            file_paths: 文件路径列表 (mp3/m4a/flac/lrc 等)
            chat_id: 目标群组 ID
            zip_name: 压缩包文件名 (多文件时使用，默认自动生成)

        Returns:
            飞书 API 响应 (最后一个包的响应)
        """
        import zipfile
        import tempfile

        MAX_FILE_SIZE = 30 * 1024 * 1024  # 30MB 飞书限制

        cid = self._resolve_chat_id(chat_id)

        if not file_paths:
            raise ValueError("file_paths 不能为空")

        # 过滤掉不存在的文件
        existing = [Path(p) for p in file_paths if Path(p).exists()]
        if not existing:
            raise FileNotFoundError("所有文件均不存在")

        if len(existing) == 1 and existing[0].stat().st_size <= MAX_FILE_SIZE:
            # 单文件且不超限，直接发送
            file_key = self._client.upload_file(str(existing[0]))
            return self._client.send_file(cid, file_key)

        # 多文件或单文件超限 → 打包 zip (自动分包)
        if not zip_name:
            zip_name = "songs"
        base_name = zip_name.removesuffix(".zip")

        # 按大小分组，每包不超过 MAX_FILE_SIZE
        # 单个文件超限的跳过并警告
        oversized = [fp for fp in existing if fp.stat().st_size > MAX_FILE_SIZE]
        sendable = [fp for fp in existing if fp.stat().st_size <= MAX_FILE_SIZE]

        if oversized:
            for fp in oversized:
                sz = fp.stat().st_size / (1024 * 1024)
                print(f"   ⚠️  跳过超限文件 ({sz:.1f} MB > 30 MB): {fp.name}")

        if not sendable:
            raise ValueError("所有文件均超过飞书 30MB 上传限制")

        groups = []
        current_group = []
        current_size = 0
        for fp in sendable:
            fsize = fp.stat().st_size
            if current_group and current_size + fsize > MAX_FILE_SIZE:
                groups.append(current_group)
                current_group = [fp]
                current_size = fsize
            else:
                current_group.append(fp)
                current_size += fsize
        if current_group:
            groups.append(current_group)

        last_result = None
        with tempfile.TemporaryDirectory() as tmp_dir:
            for i, group in enumerate(groups):
                if len(groups) == 1:
                    name = f"{base_name}.zip"
                else:
                    name = f"{base_name}_Part{i + 1}.zip"

                zip_path = Path(tmp_dir) / _sanitize_filename(name)
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for fp in group:
                        zf.write(fp, fp.name)

                print(f"   📦 上传: {name} ({zip_path.stat().st_size / 1024 / 1024:.1f} MB)")
                file_key = self._client.upload_file(str(zip_path))
                last_result = self._client.send_file(cid, file_key)

        return last_result


# ─── Webhook Pusher (无需认证) ───────────────────────────────────────────────

def _lrc_to_text(lyrics: str) -> str:
    """将 LRC 歌词转换为纯文本（去掉时间标签和元数据行）。"""
    lines = []
    for line in lyrics.splitlines():
        text = re.sub(r'\[\d{2}:\d{2}[\.\d]*\]', '', line).strip()
        if text and not re.match(r'^\[.+\]$', text):
            lines.append(text)
    return "\n".join(lines)


def _send_webhook(webhook_url: str, payload: dict) -> dict:
    """发送单条 webhook 消息。"""
    resp = requests.post(webhook_url, json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()


def push_to_webhook(webhook_url: str, song: Song) -> dict:
    """推送歌曲详情卡片 + 纯文本歌词到飞书 webhook。

    发送两条消息:
      1. 交互卡片: 歌名、歌手、时长、平台、音质等
      2. 纯文本: 完整歌词（LRC 转纯文本）

    Args:
        webhook_url: 飞书 webhook URL
        song: Song 对象（建议先 enrich 获取完整信息）

    Returns:
        卡片消息的响应 JSON
    """
    # ── 1. 歌曲详情卡片 ──
    fields = [
        {"is_short": True, "text": {"tag": "lark_md", "content": f"**歌手**: {song.artist}"}},
        {"is_short": True, "text": {"tag": "lark_md", "content": f"**时长**: {song.duration_str}"}},
        {"is_short": True, "text": {"tag": "lark_md", "content": f"**平台**: {song.source_name}"}},
        {"is_short": True, "text": {"tag": "lark_md", "content": f"**ID**: {song.id}"}},
    ]
    if song.album:
        fields.append({"is_short": True, "text": {"tag": "lark_md", "content": f"**专辑**: {song.album}"}})
    if song.size:
        fields.append({"is_short": True, "text": {"tag": "lark_md", "content": f"**大小**: {song.size}"}})
    if song.bitrate and song.bitrate != "-":
        fields.append({"is_short": True, "text": {"tag": "lark_md", "content": f"**音质**: {song.bitrate}"}})

    elements = [{"tag": "div", "fields": fields}]

    # 卡片内加歌词预览（前 4 行）
    if song.lyrics:
        preview = _format_lyrics_preview(song.lyrics, max_lines=4)
        if preview:
            elements.append({"tag": "hr"})
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"📝 **歌词预览**\n{preview}"},
            })

    source_emoji = _source_emoji(song.source)
    card_payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"🎵 {song.name}  {source_emoji} {song.source_name}"},
                "template": "blue",
            },
            "elements": elements,
        },
    }

    card_result = _send_webhook(webhook_url, card_payload)

    # ── 2. 完整歌词（纯文本消息） ──
    if song.lyrics:
        lyrics_text = _lrc_to_text(song.lyrics)
        if lyrics_text:
            text_payload = {
                "msg_type": "text",
                "content": {"text": f"📝 {song.name} - {song.artist} 完整歌词\n\n{lyrics_text}"},
            }
            _send_webhook(webhook_url, text_payload)

    return card_result


def _push_playlist_download_report(
    webhook_url: str,
    playlist_id: str,
    source: str,
    results: list,
    songs: list,
) -> dict:
    """推送歌单批量下载报告到飞书 webhook。

    Args:
        webhook_url: 飞书 webhook URL
        playlist_id: 歌单 ID
        source: 原始平台
        results: DownloadResult 列表
        songs: 原始歌曲列表

    Returns:
        飞书 API 响应
    """
    success = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    switched = [r for r in success if r.actual_source != source]

    # 构建歌曲列表文本
    lines = []
    for i, r in enumerate(results, 1):
        if r.success:
            src_tag = ""
            if r.actual_source != source:
                src_name = PLATFORMS.get(r.actual_source, r.actual_source)
                src_tag = f" 🔄{src_name}"
            lines.append(f"{i}. ✅ **{r.song.name}** - {r.song.artist}{src_tag}")
        else:
            lines.append(f"{i}. ❌ **{r.song.name}** - {r.song.artist} ({r.error})")

    body_text = "\n".join(lines)

    # 统计字段
    fields = [
        {"is_short": True, "text": {"tag": "lark_md", "content": f"**歌曲数**: {len(results)}"}},
        {"is_short": True, "text": {"tag": "lark_md", "content": f"**成功**: {len(success)}"}},
        {"is_short": True, "text": {"tag": "lark_md", "content": f"**失败**: {len(failed)}"}},
        {"is_short": True, "text": {"tag": "lark_md", "content": f"**换源**: {len(switched)}"}},
    ]

    source_name = PLATFORMS.get(source, source)
    elements = [
        {"tag": "div", "fields": fields},
        {"tag": "hr"},
        {"tag": "div", "text": {"tag": "lark_md", "content": body_text}},
    ]

    card_payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"📋 歌单下载完成 ({len(success)}/{len(results)})"},
                "template": "green" if not failed else "orange",
            },
            "elements": elements,
        },
    }

    result = _send_webhook(webhook_url, card_payload)
    print(f"✅ 下载报告已推送到飞书")
    return result


# ─── Feishu Import Helper ────────────────────────────────────────────────────

def _import_feishu_client():
    """动态导入 FeishuClient"""
    feishu_paths = [
        os.path.expanduser("~/feishu-toolkit"),
        os.path.join(os.path.dirname(__file__), "..", "feishu-toolkit"),
    ]
    for p in feishu_paths:
        if os.path.isfile(os.path.join(p, "feishu_toolkit.py")):
            if p not in sys.path:
                sys.path.insert(0, p)
            break

    try:
        from feishu_toolkit import FeishuClient
        return FeishuClient
    except ImportError:
        raise ImportError(
            "feishu_toolkit.py 未找到。请确保 ~/feishu-toolkit/feishu_toolkit.py 存在。\n"
            "飞书推送功能需要 feishu-toolkit 支持。"
        )


# ─── Formatting Helpers ──────────────────────────────────────────────────────

def _source_emoji(source: str) -> str:
    """平台对应的 emoji 标识。"""
    emoji_map = {
        "netease": "🟣",
        "qq": "🟢",
        "kugou": "🔵",
        "kuwo": "🟠",
        "migu": "🔴",
        "bilibili": "🩷",
        "fivesing": "⭐",
        "soda": "🟡",
        "jamendo": "🎼",
        "joox": "🟤",
        "qianqian": "🔶",
    }
    return emoji_map.get(source, "🎵")


def _format_lyrics_preview(lyrics: str, max_lines: int = 4) -> str:
    """从 LRC 歌词中提取纯文本预览。"""
    lines = []
    for line in lyrics.splitlines():
        # Remove LRC time tags like [00:30.42]
        text = re.sub(r'\[\d{2}:\d{2}[\.\d]*\]', '', line).strip()
        # Skip metadata lines like [ti:...], [ar:...], [al:...], [by:...], [offset:...]
        if text and not re.match(r'^\[.+\]$', text):
            lines.append(text)
        if len(lines) >= max_lines:
            break
    return "\n".join(lines)


def _split_lyrics_for_doc(lyrics: str, chunk_size: int = 20) -> list[str]:
    """将 LRC 歌词分块用于飞书文档。"""
    lines = []
    for line in lyrics.splitlines():
        text = re.sub(r'\[\d{2}:\d{2}[\.\d]*\]', '', line).strip()
        if text and not re.match(r'^\[.+\]$', text):
            lines.append(text)

    chunks = []
    for i in range(0, len(lines), chunk_size):
        chunk = "\n".join(lines[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks


def _format_song_table(songs: list[Song], show_index: bool = True) -> str:
    """格式化歌曲列表为终端友好的表格。"""
    if not songs:
        return "  (无结果)"

    lines = []
    for i, song in enumerate(songs, 1):
        prefix = f"  {i:>2}. " if show_index else "  "
        source_tag = f"[{song.source}]"
        line = f"{prefix}{song.name} - {song.artist}  ({song.duration_str})  {source_tag}"
        if song.size:
            line += f"  {song.size}"
        if song.bitrate and song.bitrate != "-":
            line += f"  {song.bitrate}"
        lines.append(line)
    return "\n".join(lines)


def _format_playlist_table(playlists: list[Playlist]) -> str:
    """格式化歌单列表为终端友好的表格。"""
    if not playlists:
        return "  (无结果)"

    lines = []
    for i, pl in enumerate(playlists, 1):
        line = f"  {i:>2}. {pl.name}  ({pl.track_count} 首)  by {pl.creator}  [{pl.source}]"
        lines.append(line)
    return "\n".join(lines)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def _print_json(data):
    """打印 JSON 数据"""
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(
        prog="music_toolkit",
        description="🎵 Music Toolkit — 音乐搜索/下载/飞书推送",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s search "晴天"                     # 全平台搜索
  %(prog)s search "晴天" --source qq          # 指定平台搜索
  %(prog)s search-playlist "周杰伦精选"       # 搜索歌单
  %(prog)s detail 0042rlGx2WHBrG qq          # 歌曲详情
  %(prog)s lyrics 0042rlGx2WHBrG qq          # 获取歌词
  %(prog)s download 0042rlGx2WHBrG qq        # 下载歌曲
  %(prog)s switch-source --name 晴天 --artist 周杰伦  # 换源
  %(prog)s platforms                          # 列出平台
  %(prog)s push-song 0042rlGx2WHBrG qq       # 推送飞书
  %(prog)s push-search "晴天"                 # 搜索+推送

环境变量:
  GO_MUSIC_DL_URL         go-music-dl 地址 (默认 http://localhost:8080)
  DOWNLOAD_DIR            下载目录 (默认 ./downloads)
  FEISHU_APP_ID           飞书 App ID (推送用)
  FEISHU_APP_SECRET       飞书 App Secret (推送用)
  FEISHU_DEFAULT_CHAT_ID  默认飞书群 ID (推送用)
        """,
    )
    sub = parser.add_subparsers(dest="command")

    # ── search ─────────────────────────────────────────────────────────────
    p = sub.add_parser("search", help="搜索歌曲")
    p.add_argument("keyword", help="搜索关键词")
    p.add_argument("--source", action="append", dest="sources", help="指定平台 (可多次)")
    p.add_argument("--json", action="store_true", dest="as_json", help="输出 JSON")

    # ── search-playlist ────────────────────────────────────────────────────
    p = sub.add_parser("search-playlist", help="搜索歌单")
    p.add_argument("keyword", help="搜索关键词")
    p.add_argument("--source", action="append", dest="sources", help="指定平台 (可多次)")
    p.add_argument("--json", action="store_true", dest="as_json", help="输出 JSON")

    # ── detail ─────────────────────────────────────────────────────────────
    p = sub.add_parser("detail", help="获取歌曲详情 (inspect + lyrics)")
    p.add_argument("song_id", help="歌曲 ID")
    p.add_argument("source", help="音源平台")
    p.add_argument("--json", action="store_true", dest="as_json", help="输出 JSON")

    # ── lyrics ─────────────────────────────────────────────────────────────
    p = sub.add_parser("lyrics", help="获取歌词")
    p.add_argument("song_id", help="歌曲 ID")
    p.add_argument("source", help="音源平台")

    # ── download ───────────────────────────────────────────────────────────
    p = sub.add_parser("download", help="下载歌曲")
    p.add_argument("song_id", help="歌曲 ID")
    p.add_argument("source", help="音源平台")
    p.add_argument("--name", default="", help="歌曲名 (文件名用)")
    p.add_argument("--artist", default="", help="歌手名 (文件名用)")
    p.add_argument("--embed", action="store_true", help="嵌入封面")
    p.add_argument("--dir", dest="save_dir", help="保存目录")

    # ── switch-source ──────────────────────────────────────────────────────
    p = sub.add_parser("switch-source", help="换源搜索")
    p.add_argument("--name", required=True, help="歌曲名")
    p.add_argument("--artist", required=True, help="歌手名")
    p.add_argument("--source", default="", help="当前平台 (排除)")
    p.add_argument("--json", action="store_true", dest="as_json", help="输出 JSON")

    # ── playlist ───────────────────────────────────────────────────────────
    p = sub.add_parser("playlist", help="获取歌单歌曲列表")
    p.add_argument("playlist_id", help="歌单 ID")
    p.add_argument("source", help="音源平台")
    p.add_argument("--json", action="store_true", dest="as_json", help="输出 JSON")

    # ── download-playlist ─────────────────────────────────────────────────
    p = sub.add_parser("download-playlist", help="批量下载歌单所有歌曲 (自动换源)")
    p.add_argument("playlist_id", help="歌单 ID")
    p.add_argument("source", help="音源平台")
    p.add_argument("--dir", dest="save_dir", help="保存目录")
    p.add_argument("--webhook", help="下载完成后推送到飞书 webhook URL")
    p.add_argument("--send-chat", dest="send_chat_id", metavar="CHAT_ID",
                   help="下载完成后发送文件到飞书群 (单首直发，多首打包zip)")
    p.add_argument("--json", action="store_true", dest="as_json", help="输出 JSON")

    # ── parse-url ──────────────────────────────────────────────────────────
    p = sub.add_parser("parse-url", help="解析音乐分享链接 → 详情 + 歌词 + 下载")
    p.add_argument("url", help="音乐分享链接 (网易云/QQ音乐/酷狗 等)")
    p.add_argument("--download", action="store_true", help="同时下载歌曲文件")
    p.add_argument("--dir", dest="save_dir", help="下载保存目录")
    p.add_argument("--webhook", help="推送到飞书 webhook URL")
    p.add_argument("--json", action="store_true", dest="as_json", help="输出 JSON")

    # ── platforms ──────────────────────────────────────────────────────────
    sub.add_parser("platforms", help="列出支持的平台")

    # ── push-song ──────────────────────────────────────────────────────────
    p = sub.add_parser("push-song", help="获取歌曲详情并推送飞书卡片")
    p.add_argument("song_id", help="歌曲 ID")
    p.add_argument("source", help="音源平台")
    p.add_argument("--chat-id", help="飞书群 ID")

    # ── push-search ────────────────────────────────────────────────────────
    p = sub.add_parser("push-search", help="搜索歌曲并推送结果到飞书")
    p.add_argument("keyword", help="搜索关键词")
    p.add_argument("--source", action="append", dest="sources", help="指定平台 (可多次)")
    p.add_argument("--chat-id", help="飞书群 ID")

    # ── push-playlist ──────────────────────────────────────────────────────
    p = sub.add_parser("push-playlist", help="获取歌单并推送到飞书")
    p.add_argument("playlist_id", help="歌单 ID")
    p.add_argument("source", help="音源平台")
    p.add_argument("--chat-id", help="飞书群 ID")

    # ── push-webhook ───────────────────────────────────────────────────────
    p = sub.add_parser("push-webhook", help="搜索歌曲并推送到飞书 webhook")
    p.add_argument("keyword", help="搜索关键词")
    p.add_argument("webhook_url", help="飞书 webhook URL")
    p.add_argument("--source", action="append", dest="sources", help="指定平台 (可多次)")

    # ── send-to-chat ──────────────────────────────────────────────────────
    p = sub.add_parser("send-to-chat", help="发送歌曲文件到飞书群 (单首直接发，多首打包zip)")
    p.add_argument("path", help="文件路径或目录路径 (目录会发送所有音频文件)")
    p.add_argument("--chat-id", help="飞书群 chat_id")
    p.add_argument("--zip-name", default="", help="压缩包名称 (多文件时)")
    p.add_argument("--include-lrc", action="store_true", help="同时包含歌词文件 (.lrc)")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    try:
        _run_command(args)
    except MusicClientError as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹ 已取消", file=sys.stderr)
        sys.exit(130)


def _run_command(args):
    """执行 CLI 子命令。"""
    client = MusicClient()

    if args.command == "search":
        songs = client.search_songs(args.keyword, sources=args.sources)
        if args.as_json:
            _print_json([s.to_dict() for s in songs])
        else:
            print(f"\n🔍 搜索: {args.keyword} (共 {len(songs)} 首)\n")
            print(_format_song_table(songs))
            if songs:
                print(f"\n💡 获取详情: python music_toolkit.py detail {songs[0].id} {songs[0].source}")

    elif args.command == "search-playlist":
        playlists = client.search_playlists(args.keyword, sources=args.sources)
        if args.as_json:
            _print_json([p.to_dict() for p in playlists])
        else:
            print(f"\n📋 歌单搜索: {args.keyword} (共 {len(playlists)} 个)\n")
            print(_format_playlist_table(playlists))
            if playlists:
                print(f"\n💡 查看歌单: python music_toolkit.py playlist {playlists[0].id} {playlists[0].source}")

    elif args.command == "detail":
        # First search to get basic info (name/artist)
        inspect_result = client.inspect(args.song_id, args.source)
        lyrics = ""
        try:
            lyrics = client.get_lyrics(args.song_id, args.source)
        except Exception:
            pass

        if args.as_json:
            _print_json({
                "id": args.song_id,
                "source": args.source,
                "inspect": inspect_result.to_dict(),
                "lyrics": lyrics,
            })
        else:
            print(f"\n🎵 歌曲详情: {args.song_id} [{args.source}]\n")
            print(f"  有效: {'✅ 是' if inspect_result.valid else '❌ 否'}")
            print(f"  大小: {inspect_result.size}")
            print(f"  码率: {inspect_result.bitrate}")
            if inspect_result.url:
                # Truncate URL for display
                url_display = inspect_result.url[:80] + "..." if len(inspect_result.url) > 80 else inspect_result.url
                print(f"  URL:  {url_display}")
            if lyrics:
                preview = _format_lyrics_preview(lyrics, max_lines=6)
                print(f"\n📝 歌词预览:\n{preview}")

    elif args.command == "lyrics":
        lyrics = client.get_lyrics(args.song_id, args.source)
        print(lyrics)

    elif args.command == "download":
        print(f"⏬ 正在下载: {args.song_id} [{args.source}] ...")
        filepath = client.download(
            args.song_id, args.source,
            name=args.name, artist=args.artist,
            embed=args.embed, save_dir=args.save_dir,
        )
        print(f"✅ 已保存: {filepath}")

    elif args.command == "switch-source":
        song = client.switch_source(args.name, args.artist, source=args.source)
        if song:
            if args.as_json:
                _print_json(song.to_dict())
            else:
                print(f"\n🔄 换源结果:\n")
                print(f"  歌名: {song.name}")
                print(f"  歌手: {song.artist}")
                print(f"  平台: {song.source_name} [{song.source}]")
                print(f"  时长: {song.duration_str}")
                if song.album:
                    print(f"  专辑: {song.album}")
                if song.link:
                    print(f"  链接: {song.link}")
                if song.score > 0:
                    print(f"  匹配度: {song.score:.0%}")
                print(f"\n💡 下载: python music_toolkit.py download {song.id} {song.source}")
        else:
            print("❌ 未找到匹配的换源结果")

    elif args.command == "playlist":
        songs = client.get_playlist_songs(args.playlist_id, args.source)
        if args.as_json:
            _print_json([s.to_dict() for s in songs])
        else:
            print(f"\n📋 歌单: {args.playlist_id} [{args.source}] (共 {len(songs)} 首)\n")
            print(_format_song_table(songs))

    elif args.command == "download-playlist":
        print(f"\n📋 获取歌单: {args.playlist_id} [{args.source}] ...")
        songs = client.get_playlist_songs(args.playlist_id, args.source)
        if not songs:
            print("❌ 歌单为空或无法获取")
            return

        print(f"   共 {len(songs)} 首，开始批量下载...\n")

        def _on_progress(idx, total, name, status):
            print(f"  [{idx:>2}/{total}] {name} — {status}")

        results = client.download_playlist(
            args.playlist_id, args.source,
            save_dir=args.save_dir,
            on_progress=_on_progress,
        )

        # 统计
        success = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        switched = [r for r in success if r.actual_source != args.source]

        print(f"\n{'─' * 50}")
        print(f"📊 下载完成: {len(success)}/{len(results)} 成功")
        if switched:
            print(f"   🔄 换源下载: {len(switched)} 首")
            for r in switched:
                src_name = PLATFORMS.get(r.actual_source, r.actual_source)
                print(f"      {r.song.name} → {src_name}")
        if failed:
            print(f"   ❌ 失败: {len(failed)} 首")
            for r in failed:
                print(f"      {r.song.name}: {r.error}")

        if args.as_json:
            _print_json([r.to_dict() for r in results])

        # 推送到飞书 webhook
        if hasattr(args, "webhook") and args.webhook and success:
            print(f"\n📨 正在推送下载报告到飞书...")
            _push_playlist_download_report(
                args.webhook, args.playlist_id, args.source,
                results, songs,
            )

        # 发送文件到飞书群
        if hasattr(args, "send_chat_id") and args.send_chat_id and success:
            file_paths = []
            for r in success:
                if r.filepath:
                    file_paths.append(r.filepath)
                if r.lrc_path:
                    file_paths.append(r.lrc_path)
            if file_paths:
                print(f"\n📤 正在发送 {len(file_paths)} 个文件到飞书群...")
                try:
                    pusher = FeishuPusher()
                    pusher.send_song_files(
                        file_paths,
                        chat_id=args.send_chat_id,
                        zip_name=f"歌单_{args.playlist_id}",
                    )
                    print(f"✅ 文件已发送到飞书群")
                except Exception as e:
                    print(f"❌ 发送失败: {e}", file=sys.stderr)

    elif args.command == "parse-url":
        # 把 URL 作为搜索关键词，go-music-dl 会自动解析
        songs = client.search_songs(args.url)
        if not songs:
            print(f"❌ 无法解析链接: {args.url}")
            return

        song = songs[0]
        enriched = client.enrich_song(song)

        if args.as_json:
            _print_json(enriched.to_dict())
        else:
            print(f"\n🎵 {enriched.name}")
            print(f"   歌手:   {enriched.artist}")
            if enriched.album:
                print(f"   专辑:   {enriched.album}")
            print(f"   时长:   {enriched.duration_str}")
            print(f"   平台:   {enriched.source_name} [{enriched.source}]")
            print(f"   ID:     {enriched.id}")
            if enriched.size:
                print(f"   大小:   {enriched.size}")
            if enriched.bitrate and enriched.bitrate != "-":
                print(f"   音质:   {enriched.bitrate}")

            if enriched.lyrics:
                print(f"\n📝 歌词:\n")
                # 打印完整歌词（去掉时间标签）
                for line in enriched.lyrics.splitlines():
                    text = re.sub(r'\[\d{2}:\d{2}[\.\d]*\]', '', line).strip()
                    if text and not re.match(r'^\[.+\]$', text):
                        print(f"   {text}")
            else:
                print("\n📝 暂无歌词")

        # 下载
        if args.download:
            # 先检查当前平台资源是否可用
            inspect_result = client.inspect(enriched.id, enriched.source, duration=enriched.duration)
            download_song = enriched

            if not inspect_result.valid:
                print(f"\n⚠️  {enriched.source_name} 资源不可用，尝试换源...")
                alt = client.switch_source(
                    enriched.name, enriched.artist,
                    source=enriched.source, duration=enriched.duration,
                )
                if alt and alt.id:
                    alt_inspect = client.inspect(alt.id, alt.source, duration=alt.duration)
                    if alt_inspect.valid:
                        download_song = Song(
                            id=alt.id, source=alt.source,
                            name=alt.name or enriched.name,
                            artist=alt.artist or enriched.artist,
                            duration=alt.duration, cover=alt.cover,
                            album=alt.album, extra=alt.extra,
                            url=alt_inspect.url, size=alt_inspect.size,
                            bitrate=alt_inspect.bitrate,
                        )
                        print(f"   找到可用源: {download_song.source_name} [{download_song.source}]"
                              f"  {download_song.size}")
                    else:
                        print(f"❌ 换源后仍无法下载，该歌曲可能有版权限制")
                        return
                else:
                    print(f"❌ 未找到可用的替代源，该歌曲可能有版权限制")
                    return

            print(f"\n⏬ 正在下载...")
            filepath = client.download(
                download_song.id, download_song.source,
                name=download_song.name, artist=download_song.artist,
                cover=download_song.cover, extra=download_song.extra,
                save_dir=args.save_dir,
            )
            print(f"✅ 已保存: {filepath}")

            # 同时下载歌词文件
            if enriched.lyrics:
                lrc_path = client.download_lyrics_file(
                    enriched.id, enriched.source,
                    name=enriched.name, artist=enriched.artist,
                    save_dir=args.save_dir,
                )
                print(f"✅ 歌词: {lrc_path}")

        # 推送飞书 webhook
        if hasattr(args, "webhook") and args.webhook:
            result = push_to_webhook(args.webhook, enriched)
            print(f"\n📨 已推送到飞书 (卡片 + 歌词)")

    elif args.command == "platforms":
        print("\n🎵 支持的平台:\n")
        for code, name in PLATFORMS.items():
            print(f"  {code:<12} {name}")
        print(f"\n  共 {len(PLATFORMS)} 个平台")

    elif args.command == "push-song":
        # Enrich with inspect + lyrics
        inspect_result = client.inspect(args.song_id, args.source)
        lyrics = ""
        try:
            lyrics = client.get_lyrics(args.song_id, args.source)
        except Exception:
            pass

        song = Song(
            id=args.song_id,
            source=args.source,
            name=args.song_id,  # Will use ID as name if not found
            artist="",
            duration=0,
            cover="",
            url=inspect_result.url,
            size=inspect_result.size,
            bitrate=inspect_result.bitrate,
            lyrics=lyrics,
        )

        pusher = FeishuPusher()
        pusher.push_song_card(song, chat_id=args.chat_id)
        print("✅ 歌曲详情已推送到飞书")

    elif args.command == "push-search":
        songs = client.search_songs(args.keyword, sources=args.sources)
        if not songs:
            print(f"❌ 未找到: {args.keyword}")
            return
        # Enrich first few songs with inspect
        enriched = []
        for song in songs[:5]:
            try:
                enriched.append(client.enrich_song(song))
            except Exception:
                enriched.append(song)
        # Keep the rest as-is
        enriched.extend(songs[5:])

        pusher = FeishuPusher()
        pusher.push_search_results(enriched, args.keyword, chat_id=args.chat_id)
        print(f"✅ 搜索结果 ({len(songs)} 首) 已推送到飞书")

    elif args.command == "push-playlist":
        songs = client.get_playlist_songs(args.playlist_id, args.source)
        playlist = Playlist(
            id=args.playlist_id,
            source=args.source,
            name=f"歌单 {args.playlist_id}",
            cover="",
            track_count=len(songs),
        )
        pusher = FeishuPusher()
        pusher.push_playlist_card(playlist, songs=songs, chat_id=args.chat_id)
        print(f"✅ 歌单 ({len(songs)} 首) 已推送到飞书")

    elif args.command == "push-webhook":
        songs = client.search_songs(args.keyword, sources=args.sources)
        if not songs:
            print(f"❌ 未找到: {args.keyword}")
            return

        # 找到最匹配的歌曲（优先原唱，非 Cover 版本）
        song = songs[0]
        for s in songs:
            if "Cover" not in s.name and "cover" not in s.name.lower():
                song = s
                break

        # 获取完整详情
        enriched = client.enrich_song(song)

        # 推送到 webhook
        result = push_to_webhook(args.webhook_url, enriched)
        print(f"✅ 已推送到飞书 webhook")
        print(f"   歌曲: {enriched.name}")
        print(f"   歌手: {enriched.artist}")
        print(f"   平台: {enriched.source_name}")
        print(f"   响应: {result.get('msg', 'success')}")

    elif args.command == "send-to-chat":
        target = Path(args.path)
        audio_exts = {".mp3", ".m4a", ".flac", ".wav", ".ogg", ".opus", ".aac", ".wma"}
        lrc_ext = {".lrc"}

        if target.is_file():
            file_paths = [target]
        elif target.is_dir():
            # 收集目录下的音频文件
            file_paths = sorted([
                f for f in target.iterdir()
                if f.suffix.lower() in audio_exts
            ])
            if args.include_lrc:
                lrc_paths = sorted([
                    f for f in target.iterdir()
                    if f.suffix.lower() in lrc_ext
                ])
                file_paths.extend(lrc_paths)
        else:
            print(f"❌ 路径不存在: {args.path}", file=sys.stderr)
            sys.exit(1)

        if not file_paths:
            print(f"❌ 未找到音频文件: {args.path}", file=sys.stderr)
            sys.exit(1)

        print(f"📤 准备发送 {len(file_paths)} 个文件到飞书群...")
        for f in file_paths:
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"   {f.name}  ({size_mb:.1f} MB)")

        if len(file_paths) > 1:
            zip_name = args.zip_name or target.name or "songs"
            print(f"\n📦 多文件，打包为: {zip_name}.zip")

        pusher = FeishuPusher()
        result = pusher.send_song_files(
            file_paths,
            chat_id=args.chat_id,
            zip_name=args.zip_name or (target.name if target.is_dir() else ""),
        )
        print(f"✅ 文件已发送到飞书群")


if __name__ == "__main__":
    main()
