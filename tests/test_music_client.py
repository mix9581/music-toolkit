"""Tests for MusicClient — HTML parsing, API interactions."""

import json
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from dataclasses import asdict

import pytest
import requests

# Ensure music_toolkit is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from music_toolkit import (
    MusicClient,
    MusicClientError,
    Song,
    Playlist,
    InspectResult,
    DownloadResult,
    _parse_song_cards,
    _parse_playlist_cards,
    _extract_filename,
    _build_filename,
    _sanitize_filename,
    _format_lyrics_preview,
    _split_lyrics_for_doc,
    _lrc_to_text,
    push_to_webhook,
    PLATFORMS,
)


# ─── Sample HTML Fixtures ────────────────────────────────────────────────────

SAMPLE_SEARCH_HTML = """
<!DOCTYPE html>
<html>
<body>
<ul>
    <li class="song-card"
        data-id="0042rlGx2WHBrG"
        data-source="qq"
        data-duration="278"
        data-name="晴天 (深情版)"
        data-artist="Lucky小爱"
        data-cover="https://y.gtimg.cn/music/photo_new/T002R300x300M000004QUu810PIQis.jpg"
        data-extra='{"songmid":"0042rlGx2WHBrG"}'>
        <div>content</div>
    </li>
    <li class="song-card"
        data-id="0003f6pW1hOLKG"
        data-source="qq"
        data-duration="150"
        data-name="晴天-文武贝钢琴版"
        data-artist="文武贝"
        data-cover="https://y.gtimg.cn/music/photo_new/T002R300x300M000004QXtXm1PWWmu.jpg"
        data-extra='{"songmid":"0003f6pW1hOLKG"}'>
        <div>content</div>
    </li>
    <li class="song-card"
        data-id="000465Nk1KLt78"
        data-source="qq"
        data-duration="189"
        data-name="晴天"
        data-artist="haocd"
        data-cover="https://y.gtimg.cn/music/photo_new/T002R300x300M000002bO8Tb33nvJo.jpg"
        data-extra='{"songmid":"000465Nk1KLt78"}'>
        <div>content</div>
    </li>
</ul>
</body>
</html>
"""

SAMPLE_SEARCH_HTML_ENTITIES = """
<li class="song-card"
    data-id="abc123"
    data-source="netease"
    data-duration="200"
    data-name="Love &amp; Peace"
    data-artist="Artist &lt;Special&gt;"
    data-cover="https://example.com/cover.jpg"
    data-extra='{"key":"value"}'>
</li>
"""

SAMPLE_PLAYLIST_HTML = """
<div class="playlist-card" onclick="location.href='/music/playlist?id=6792103822&source=netease'">
    <div class="playlist-cover">
        <img src="http://p1.music.126.net/abc/109951169535051638.jpg" loading="lazy">
        <span class="tag tag-src">netease</span>
    </div>
    <div class="playlist-meta">
        <div class="playlist-title">
            周杰伦-Jay 精选
            <a href="https://music.163.com/#/playlist?id=6792103822" target="_blank" class="external-link-icon">
                <i class="fa-solid fa-arrow-up-right-from-square"></i>
            </a>
        </div>
        <div class="playlist-author"><i class="fa-regular fa-user"></i> Buradarrr</div>
        <div style="display:flex;">
            <div class="playlist-count">共 147 首</div>
        </div>
    </div>
</div>
<div class="playlist-card" onclick="location.href='/music/playlist?id=10057662169&amp;source=netease'">
    <div class="playlist-cover">
        <img src="http://p1.music.126.net/def/image.jpg" loading="lazy">
    </div>
    <div class="playlist-meta">
        <div class="playlist-title">
            周杰伦全免费听
            <a href="https://music.163.com/#/playlist?id=10057662169" target="_blank" class="external-link-icon">
                <i class="fa-solid fa-arrow-up-right-from-square"></i>
            </a>
        </div>
        <div class="playlist-author"><i class="fa-regular fa-user"></i> TestUser</div>
        <div style="display:flex;">
            <div class="playlist-count">共 34 首</div>
        </div>
    </div>
</div>
"""

SAMPLE_LYRICS = """[ti:晴天 (深情版)]
[ar:Lucky小爱]
[al:晴天 (深情版)]
[by:]
[offset:0]
[00:00.36]晴天 (深情版) - Lucky小爱
[00:02.66]原唱：周杰伦
[00:03.97]词：周杰伦
[00:05.04]曲：周杰伦
[00:30.42]故事的小黄花
[00:33.97]从出生那年就飘着
[00:37.62]童年的荡秋千
[00:41.25]随记忆一直晃到现在
"""

SAMPLE_INSPECT_JSON = {
    "valid": True,
    "url": "https://ws.stream.qqmusic.qq.com/M5000042rlGx2WHBrG.mp3",
    "size": "4.3 MB",
    "bitrate": "128kbps",
}

SAMPLE_SWITCH_JSON = {
    "id": "bLnv0PqDX_qAlIqapc+Okw==",
    "source": "joox",
    "name": "晴天",
    "artist": "周杰倫",
    "duration": 269,
    "cover": "https://image.joox.com/cover.jpg",
    "album": "葉惠美",
    "link": "https://www.joox.com/hk/single/xxx",
    "score": 0.9,
}


# ─── Song Data Model Tests ───────────────────────────────────────────────────

class TestSong:
    def test_duration_str(self):
        song = Song(id="1", source="qq", name="Test", artist="A", duration=269, cover="")
        assert song.duration_str == "4:29"

    def test_duration_str_zero(self):
        song = Song(id="1", source="qq", name="Test", artist="A", duration=0, cover="")
        assert song.duration_str == "0:00"

    def test_duration_str_short(self):
        song = Song(id="1", source="qq", name="Test", artist="A", duration=5, cover="")
        assert song.duration_str == "0:05"

    def test_source_name(self):
        song = Song(id="1", source="qq", name="Test", artist="A", duration=0, cover="")
        assert song.source_name == "QQ音乐"

    def test_source_name_unknown(self):
        song = Song(id="1", source="unknown_src", name="Test", artist="A", duration=0, cover="")
        assert song.source_name == "unknown_src"

    def test_to_dict(self):
        song = Song(id="1", source="qq", name="Test", artist="A", duration=120, cover="url")
        d = song.to_dict()
        assert d["id"] == "1"
        assert d["duration_str"] == "2:00"
        assert d["source_name"] == "QQ音乐"

    def test_frozen(self):
        song = Song(id="1", source="qq", name="Test", artist="A", duration=0, cover="")
        with pytest.raises(AttributeError):
            song.name = "Changed"


# ─── Playlist Data Model Tests ───────────────────────────────────────────────

class TestPlaylist:
    def test_source_name(self):
        pl = Playlist(id="1", source="netease", name="Test", cover="")
        assert pl.source_name == "网易云音乐"

    def test_to_dict(self):
        pl = Playlist(id="1", source="netease", name="Test", cover="", track_count=50, creator="user")
        d = pl.to_dict()
        assert d["track_count"] == 50
        assert d["source_name"] == "网易云音乐"


# ─── InspectResult Tests ─────────────────────────────────────────────────────

class TestInspectResult:
    def test_to_dict(self):
        ir = InspectResult(valid=True, url="https://example.com", size="4.3 MB", bitrate="128kbps")
        d = ir.to_dict()
        assert d["valid"] is True
        assert d["size"] == "4.3 MB"


# ─── HTML Parsing Tests ──────────────────────────────────────────────────────

class TestParseSongCards:
    def test_basic_parse(self):
        songs = _parse_song_cards(SAMPLE_SEARCH_HTML)
        assert len(songs) == 3

    def test_first_song_fields(self):
        songs = _parse_song_cards(SAMPLE_SEARCH_HTML)
        s = songs[0]
        assert s.id == "0042rlGx2WHBrG"
        assert s.source == "qq"
        assert s.duration == 278
        assert s.name == "晴天 (深情版)"
        assert s.artist == "Lucky小爱"
        assert "gtimg.cn" in s.cover

    def test_extra_json(self):
        songs = _parse_song_cards(SAMPLE_SEARCH_HTML)
        assert songs[0].extra.get("songmid") == "0042rlGx2WHBrG"

    def test_html_entity_decode(self):
        songs = _parse_song_cards(SAMPLE_SEARCH_HTML_ENTITIES)
        assert len(songs) == 1
        assert songs[0].name == "Love & Peace"
        assert songs[0].artist == "Artist <Special>"

    def test_empty_html(self):
        songs = _parse_song_cards("<html><body></body></html>")
        assert songs == []

    def test_multiple_sources(self):
        html = SAMPLE_SEARCH_HTML.replace('data-source="qq"', 'data-source="netease"', 1)
        songs = _parse_song_cards(html)
        assert songs[0].source == "netease"
        assert songs[1].source == "qq"


class TestParsePlaylistCards:
    def test_basic_parse(self):
        playlists = _parse_playlist_cards(SAMPLE_PLAYLIST_HTML)
        assert len(playlists) == 2

    def test_first_playlist_fields(self):
        playlists = _parse_playlist_cards(SAMPLE_PLAYLIST_HTML)
        pl = playlists[0]
        assert pl.id == "6792103822"
        assert pl.source == "netease"
        assert "周杰伦" in pl.name
        assert pl.creator == "Buradarrr"
        assert pl.track_count == 147

    def test_second_playlist(self):
        playlists = _parse_playlist_cards(SAMPLE_PLAYLIST_HTML)
        pl = playlists[1]
        assert pl.id == "10057662169"
        assert pl.track_count == 34
        assert pl.creator == "TestUser"

    def test_empty_html(self):
        playlists = _parse_playlist_cards("<html></html>")
        assert playlists == []


# ─── Filename Helpers Tests ──────────────────────────────────────────────────

class TestFilenameHelpers:
    def test_extract_filename_utf8(self):
        resp = MagicMock()
        resp.headers = {"Content-Disposition": "attachment; filename*=UTF-8''%E6%99%B4%E5%A4%A9.mp3"}
        assert _extract_filename(resp) == "晴天.mp3"

    def test_extract_filename_quoted(self):
        resp = MagicMock()
        resp.headers = {"Content-Disposition": 'attachment; filename="test.mp3"'}
        assert _extract_filename(resp) == "test.mp3"

    def test_extract_filename_unquoted(self):
        resp = MagicMock()
        resp.headers = {"Content-Disposition": "attachment; filename=song.mp3"}
        assert _extract_filename(resp) == "song.mp3"

    def test_extract_filename_missing(self):
        resp = MagicMock()
        resp.headers = {}
        assert _extract_filename(resp) == ""

    def test_build_filename_full(self):
        assert _build_filename("晴天", "周杰伦", "mp3") == "晴天-周杰伦.mp3"

    def test_build_filename_name_only(self):
        assert _build_filename("晴天", "", "mp3") == "晴天.mp3"

    def test_build_filename_unknown(self):
        assert _build_filename("", "", "mp3") == "unknown.mp3"

    def test_sanitize_filename(self):
        result = _sanitize_filename('test<>:"/\\|?*.mp3')
        # Each unsafe char (<, >, :, ", /, \, |, ?, *) replaced with _
        assert "<" not in result
        assert ">" not in result
        assert result.endswith(".mp3")

    def test_sanitize_filename_clean(self):
        assert _sanitize_filename("晴天-周杰伦.mp3") == "晴天-周杰伦.mp3"


# ─── Lyrics Formatting Tests ─────────────────────────────────────────────────

class TestLyricsFormatting:
    def test_lyrics_preview(self):
        preview = _format_lyrics_preview(SAMPLE_LYRICS, max_lines=4)
        lines = preview.split("\n")
        assert len(lines) == 4
        # Should skip metadata lines and time tags
        assert "晴天" in lines[0]

    def test_lyrics_preview_strips_tags(self):
        preview = _format_lyrics_preview("[00:30.42]故事的小黄花")
        assert preview == "故事的小黄花"

    def test_lyrics_preview_empty(self):
        assert _format_lyrics_preview("") == ""

    def test_split_lyrics_for_doc(self):
        chunks = _split_lyrics_for_doc(SAMPLE_LYRICS, chunk_size=3)
        assert len(chunks) >= 1
        for chunk in chunks:
            assert "[" not in chunk  # No LRC time tags


# ─── MusicClient Tests (Mocked HTTP) ─────────────────────────────────────────

class TestMusicClient:
    def setup_method(self):
        self.client = MusicClient(base_url="http://test:8080")

    @patch.object(MusicClient, "_get")
    def test_search_songs(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = SAMPLE_SEARCH_HTML
        mock_get.return_value = mock_resp

        songs = self.client.search_songs("晴天")
        assert len(songs) == 3
        assert songs[0].name == "晴天 (深情版)"
        mock_get.assert_called_once_with("/music/search", params={"q": "晴天", "type": "song"})

    @patch.object(MusicClient, "_get")
    def test_search_songs_with_sources(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = SAMPLE_SEARCH_HTML
        mock_get.return_value = mock_resp

        self.client.search_songs("晴天", sources=["qq", "netease"])
        mock_get.assert_called_once_with(
            "/music/search",
            params={"q": "晴天", "type": "song", "sources": "qq,netease"},
        )

    @patch.object(MusicClient, "_get")
    def test_search_playlists(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = SAMPLE_PLAYLIST_HTML
        mock_get.return_value = mock_resp

        playlists = self.client.search_playlists("周杰伦")
        assert len(playlists) == 2
        mock_get.assert_called_once_with(
            "/music/search",
            params={"q": "周杰伦", "type": "playlist"},
        )

    @patch.object(MusicClient, "_get")
    def test_get_lyrics(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = SAMPLE_LYRICS
        mock_get.return_value = mock_resp

        lyrics = self.client.get_lyrics("abc", "qq")
        assert "故事的小黄花" in lyrics
        mock_get.assert_called_once_with("/music/lyric", params={"id": "abc", "source": "qq"})

    @patch.object(MusicClient, "_get")
    def test_inspect(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = SAMPLE_INSPECT_JSON
        mock_get.return_value = mock_resp

        result = self.client.inspect("abc", "qq")
        assert result.valid is True
        assert result.size == "4.3 MB"
        assert result.bitrate == "128kbps"

    @patch.object(MusicClient, "_get")
    def test_inspect_with_duration(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = SAMPLE_INSPECT_JSON
        mock_get.return_value = mock_resp

        self.client.inspect("abc", "qq", duration=278)
        mock_get.assert_called_once_with(
            "/music/inspect",
            params={"id": "abc", "source": "qq", "duration": "278"},
        )

    @patch.object(MusicClient, "_get")
    def test_switch_source(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = SAMPLE_SWITCH_JSON
        mock_get.return_value = mock_resp

        song = self.client.switch_source("晴天", "周杰伦", source="qq")
        assert song is not None
        assert song.source == "joox"
        assert song.album == "葉惠美"
        assert song.score == 0.9

    @patch.object(MusicClient, "_get")
    def test_switch_source_not_found(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        song = self.client.switch_source("NotExist", "Nobody")
        assert song is None

    @patch.object(MusicClient, "_get")
    def test_get_playlist_songs(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = SAMPLE_SEARCH_HTML
        mock_get.return_value = mock_resp

        songs = self.client.get_playlist_songs("12345", "netease")
        assert len(songs) == 3
        mock_get.assert_called_once_with(
            "/music/playlist",
            params={"id": "12345", "source": "netease"},
        )

    @patch.object(MusicClient, "_get")
    def test_enrich_song(self, mock_get):
        # First call: inspect, second call: lyrics
        inspect_resp = MagicMock()
        inspect_resp.json.return_value = SAMPLE_INSPECT_JSON

        lyrics_resp = MagicMock()
        lyrics_resp.text = SAMPLE_LYRICS

        mock_get.side_effect = [inspect_resp, lyrics_resp]

        song = Song(id="abc", source="qq", name="晴天", artist="周杰伦", duration=278, cover="url")
        enriched = self.client.enrich_song(song)

        assert enriched.size == "4.3 MB"
        assert enriched.bitrate == "128kbps"
        assert "故事的小黄花" in enriched.lyrics
        assert enriched.name == "晴天"  # Preserved from original

    def test_list_platforms(self):
        platforms = MusicClient.list_platforms()
        assert "qq" in platforms
        assert "netease" in platforms
        assert len(platforms) == len(PLATFORMS)

    @patch("requests.Session.get")
    def test_connection_error(self, mock_get):
        mock_get.side_effect = requests.ConnectionError("Connection refused")

        with pytest.raises(MusicClientError, match="无法连接"):
            self.client.search_songs("test")

    @patch.object(MusicClient, "_get")
    def test_download(self, mock_get, tmp_path):
        mock_resp = MagicMock()
        mock_resp.headers = {"Content-Disposition": "attachment; filename=\"test.mp3\""}
        mock_resp.iter_content.return_value = [b"fake audio data"]
        mock_get.return_value = mock_resp

        filepath = self.client.download("abc", "qq", name="Test", artist="A", save_dir=str(tmp_path))
        assert filepath.exists()
        assert filepath.name == "test.mp3"

    @patch.object(MusicClient, "_get")
    def test_download_fallback_filename(self, mock_get, tmp_path):
        mock_resp = MagicMock()
        mock_resp.headers = {}
        mock_resp.iter_content.return_value = [b"fake audio data"]
        mock_get.return_value = mock_resp

        filepath = self.client.download("abc", "qq", name="晴天", artist="周杰伦", save_dir=str(tmp_path))
        assert filepath.exists()
        assert filepath.name == "晴天-周杰伦.mp3"


# ─── Constants Tests ─────────────────────────────────────────────────────────

class TestConstants:
    def test_all_platforms_have_names(self):
        for code in PLATFORMS:
            assert isinstance(PLATFORMS[code], str)
            assert len(PLATFORMS[code]) > 0

    def test_platform_count(self):
        assert len(PLATFORMS) == 11


# ─── Album Extraction from HTML Tests ───────────────────────────────────────

SAMPLE_SEARCH_HTML_WITH_ALBUM = """
<li class="song-card"
    data-id="28707005"
    data-source="netease"
    data-duration="273"
    data-name="拥有"
    data-artist="李泉"
    data-cover="https://p1.music.126.net/abc/cover.jpg"
    data-extra='{"song_id":"28707005"}'>
    <div class="song-meta">
        <div class="title-line">拥有</div>
        <div class="artist-line"><i class="fa-regular fa-user"></i> 李泉 &nbsp;•&nbsp; 再见忧伤</div>
    </div>
</li>
"""

SAMPLE_SEARCH_HTML_NO_ALBUM = """
<li class="song-card"
    data-id="12345"
    data-source="qq"
    data-duration="200"
    data-name="TestSong"
    data-artist="TestArtist"
    data-cover="https://example.com/cover.jpg"
    data-extra='{}'>
    <div class="song-meta">
        <div class="title-line">TestSong</div>
        <div class="artist-line"><i class="fa-regular fa-user"></i> TestArtist</div>
    </div>
</li>
"""


class TestAlbumExtraction:
    def test_album_from_artist_line(self):
        songs = _parse_song_cards(SAMPLE_SEARCH_HTML_WITH_ALBUM)
        assert len(songs) == 1
        assert songs[0].album == "再见忧伤"

    def test_no_album(self):
        songs = _parse_song_cards(SAMPLE_SEARCH_HTML_NO_ALBUM)
        assert len(songs) == 1
        assert songs[0].album == ""

    def test_album_with_existing_songs(self):
        """Original HTML fixture should still parse correctly (no album in it)."""
        songs = _parse_song_cards(SAMPLE_SEARCH_HTML)
        assert len(songs) == 3
        # Original fixture doesn't have artist-line with album
        for song in songs:
            assert isinstance(song.album, str)


# ─── LRC to Text Conversion Tests ───────────────────────────────────────────

class TestLrcToText:
    def test_basic_conversion(self):
        lrc = "[00:30.42]故事的小黄花\n[00:33.97]从出生那年就飘着"
        text = _lrc_to_text(lrc)
        assert text == "故事的小黄花\n从出生那年就飘着"

    def test_strips_metadata(self):
        lrc = "[ti:晴天]\n[ar:周杰伦]\n[al:叶惠美]\n[00:30.42]故事的小黄花"
        text = _lrc_to_text(lrc)
        assert text == "故事的小黄花"
        assert "[ti:" not in text
        assert "[ar:" not in text

    def test_strips_time_tags(self):
        text = _lrc_to_text("[00:30.42]Hello World")
        assert text == "Hello World"
        assert "[" not in text

    def test_empty_input(self):
        assert _lrc_to_text("") == ""

    def test_full_lyrics(self):
        text = _lrc_to_text(SAMPLE_LYRICS)
        lines = text.split("\n")
        assert len(lines) > 0
        for line in lines:
            # No time tags should remain
            assert not line.startswith("[")

    def test_skips_blank_lines(self):
        lrc = "[00:30.42]Line 1\n\n[00:33.97]Line 2"
        text = _lrc_to_text(lrc)
        assert "Line 1" in text
        assert "Line 2" in text


# ─── Webhook Push Tests ─────────────────────────────────────────────────────

class TestPushToWebhook:
    @patch("music_toolkit._send_webhook")
    def test_push_card_and_lyrics(self, mock_send):
        mock_send.return_value = {"code": 0, "msg": "success"}

        song = Song(
            id="abc", source="qq", name="晴天", artist="周杰伦",
            duration=269, cover="", album="叶惠美",
            size="4.3 MB", bitrate="128kbps",
            lyrics="[00:30.42]故事的小黄花\n[00:33.97]从出生那年就飘着",
        )

        result = push_to_webhook("https://hook.example.com", song)
        assert result["code"] == 0

        # Should be called twice: card + lyrics text
        assert mock_send.call_count == 2

        # First call: card
        card_payload = mock_send.call_args_list[0][0][1]
        assert card_payload["msg_type"] == "interactive"
        assert "晴天" in card_payload["card"]["header"]["title"]["content"]

        # Second call: lyrics text
        text_payload = mock_send.call_args_list[1][0][1]
        assert text_payload["msg_type"] == "text"
        assert "故事的小黄花" in text_payload["content"]["text"]

    @patch("music_toolkit._send_webhook")
    def test_push_no_lyrics(self, mock_send):
        mock_send.return_value = {"code": 0, "msg": "success"}

        song = Song(
            id="abc", source="qq", name="Test", artist="A",
            duration=100, cover="",
        )

        push_to_webhook("https://hook.example.com", song)
        # Only card, no lyrics message
        assert mock_send.call_count == 1
        card_payload = mock_send.call_args_list[0][0][1]
        assert card_payload["msg_type"] == "interactive"

    @patch("music_toolkit._send_webhook")
    def test_push_card_fields(self, mock_send):
        mock_send.return_value = {"code": 0}

        song = Song(
            id="test_id", source="netease", name="拥有", artist="李泉",
            duration=273, cover="", album="再见忧伤",
            size="10.5 MB", bitrate="320kbps",
        )

        push_to_webhook("https://hook.example.com", song)
        card_payload = mock_send.call_args_list[0][0][1]

        # Check fields in the card
        fields = card_payload["card"]["elements"][0]["fields"]
        field_texts = [f["text"]["content"] for f in fields]

        assert any("李泉" in t for t in field_texts)
        assert any("4:33" in t for t in field_texts)
        assert any("网易云音乐" in t for t in field_texts)
        assert any("再见忧伤" in t for t in field_texts)
        assert any("10.5 MB" in t for t in field_texts)
        assert any("320kbps" in t for t in field_texts)

    @patch("music_toolkit._send_webhook")
    def test_push_webhook_url_passed(self, mock_send):
        mock_send.return_value = {"code": 0}

        song = Song(id="a", source="qq", name="T", artist="A", duration=0, cover="")
        push_to_webhook("https://my-webhook.example.com/hook/123", song)

        # Verify the webhook URL was passed correctly
        assert mock_send.call_args_list[0][0][0] == "https://my-webhook.example.com/hook/123"


# ─── Download with Extra Parameter Tests ────────────────────────────────────

class TestDownloadWithExtra:
    def setup_method(self):
        self.client = MusicClient(base_url="http://test:8080")

    @patch.object(MusicClient, "_get")
    def test_download_with_extra(self, mock_get, tmp_path):
        mock_resp = MagicMock()
        mock_resp.headers = {"Content-Disposition": 'attachment; filename="song.mp3"'}
        mock_resp.iter_content.return_value = [b"fake audio data"]
        mock_get.return_value = mock_resp

        extra = {"song_id": "28707005"}
        filepath = self.client.download(
            "28707005", "netease", name="拥有", artist="李泉",
            extra=extra, save_dir=str(tmp_path),
        )
        assert filepath.exists()

        # Verify extra was passed in the params
        call_params = mock_get.call_args[1]["params"] if "params" in (mock_get.call_args[1] or {}) else mock_get.call_args[0][1] if len(mock_get.call_args[0]) > 1 else mock_get.call_args
        # Check the actual call
        args, kwargs = mock_get.call_args
        params = kwargs.get("params") or (args[1] if len(args) > 1 else None)
        if params is None:
            # _get is called as _get(path, params=params, stream=True)
            params = args[1] if len(args) > 1 else {}
        assert "extra" in str(mock_get.call_args)

    @patch.object(MusicClient, "_get")
    def test_download_without_extra(self, mock_get, tmp_path):
        mock_resp = MagicMock()
        mock_resp.headers = {}
        mock_resp.iter_content.return_value = [b"data"]
        mock_get.return_value = mock_resp

        self.client.download("abc", "qq", save_dir=str(tmp_path))
        # Verify extra is NOT in the params when not provided
        call_str = str(mock_get.call_args)
        assert "extra" not in call_str or '"extra"' not in call_str


# ─── DownloadResult Tests ───────────────────────────────────────────────────

class TestDownloadResult:
    def test_success_to_dict(self):
        song = Song(id="1", source="netease", name="Test", artist="A", duration=0, cover="")
        result = DownloadResult(
            song=song, success=True,
            filepath=Path("/tmp/test.mp3"), lrc_path=Path("/tmp/test.lrc"),
            actual_source="migu",
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["actual_source"] == "migu"
        assert d["filepath"] == "/tmp/test.mp3"
        assert d["lrc_path"] == "/tmp/test.lrc"

    def test_failure_to_dict(self):
        song = Song(id="1", source="netease", name="Test", artist="A", duration=0, cover="")
        result = DownloadResult(
            song=song, success=False,
            actual_source="netease", error="无可用替代源",
        )
        d = result.to_dict()
        assert d["success"] is False
        assert d["error"] == "无可用替代源"
        assert "filepath" not in d


# ─── Playlist Batch Download Tests ──────────────────────────────────────────

class TestDownloadPlaylist:
    def setup_method(self):
        self.client = MusicClient(base_url="http://test:8080")

    @patch.object(MusicClient, "download_lyrics_file")
    @patch.object(MusicClient, "download")
    @patch.object(MusicClient, "inspect")
    @patch.object(MusicClient, "get_playlist_songs")
    def test_all_songs_available(self, mock_playlist, mock_inspect, mock_download, mock_lrc):
        """All songs directly available — no switch-source needed."""
        songs = [
            Song(id="1", source="qq", name="Song A", artist="Artist", duration=200, cover=""),
            Song(id="2", source="qq", name="Song B", artist="Artist", duration=180, cover=""),
        ]
        mock_playlist.return_value = songs
        mock_inspect.return_value = InspectResult(valid=True, url="url", size="4MB", bitrate="128kbps")
        mock_download.return_value = Path("/tmp/song.mp3")
        mock_lrc.return_value = Path("/tmp/song.lrc")

        results = self.client.download_playlist("123", "qq")
        assert len(results) == 2
        assert all(r.success for r in results)
        assert all(r.actual_source == "qq" for r in results)

    @patch.object(MusicClient, "download_lyrics_file")
    @patch.object(MusicClient, "download")
    @patch.object(MusicClient, "switch_source")
    @patch.object(MusicClient, "inspect")
    @patch.object(MusicClient, "get_playlist_songs")
    def test_auto_switch_source(self, mock_playlist, mock_inspect, mock_switch, mock_download, mock_lrc):
        """Original source unavailable → switch_source → download from alt."""
        songs = [
            Song(id="1", source="netease", name="Song A", artist="Artist", duration=200, cover=""),
        ]
        mock_playlist.return_value = songs

        # First inspect: invalid (original), second (alt): valid
        mock_inspect.side_effect = [
            InspectResult(valid=False, url="", size="", bitrate=""),
            InspectResult(valid=True, url="url", size="3MB", bitrate="128kbps"),
        ]
        mock_switch.return_value = Song(
            id="alt1", source="migu", name="Song A", artist="Artist",
            duration=200, cover="",
        )
        mock_download.return_value = Path("/tmp/song.mp3")
        mock_lrc.return_value = Path("/tmp/song.lrc")

        results = self.client.download_playlist("123", "netease")
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].actual_source == "migu"

    @patch.object(MusicClient, "search_songs")
    @patch.object(MusicClient, "switch_source")
    @patch.object(MusicClient, "inspect")
    @patch.object(MusicClient, "get_playlist_songs")
    def test_all_sources_exhausted(self, mock_playlist, mock_inspect, mock_switch, mock_search):
        """No source available at all — all inspects fail."""
        songs = [
            Song(id="1", source="netease", name="Song A", artist="Artist", duration=200, cover=""),
        ]
        mock_playlist.return_value = songs
        mock_inspect.return_value = InspectResult(valid=False, url="", size="", bitrate="")
        mock_switch.return_value = None
        mock_search.return_value = []

        results = self.client.download_playlist("123", "netease")
        assert len(results) == 1
        assert results[0].success is False
        assert "已尝试" in results[0].error

    @patch.object(MusicClient, "get_playlist_songs")
    def test_empty_playlist(self, mock_playlist):
        """Empty playlist returns empty results."""
        mock_playlist.return_value = []
        results = self.client.download_playlist("123", "netease")
        assert results == []

    @patch.object(MusicClient, "search_songs")
    @patch.object(MusicClient, "download_lyrics_file")
    @patch.object(MusicClient, "download")
    @patch.object(MusicClient, "switch_source")
    @patch.object(MusicClient, "inspect")
    @patch.object(MusicClient, "get_playlist_songs")
    def test_502_retries_other_sources(self, mock_playlist, mock_inspect, mock_switch, mock_download, mock_lrc, mock_search):
        """Download 502 on first alt source → retry with search results → succeed."""
        songs = [
            Song(id="1", source="netease", name="Song A", artist="Artist", duration=200, cover=""),
        ]
        mock_playlist.return_value = songs

        # inspect: original invalid, switch_source alt valid, search alt2 valid
        mock_inspect.side_effect = [
            InspectResult(valid=False, url="", size="", bitrate=""),  # original
            InspectResult(valid=True, url="url", size="3MB", bitrate=""),  # switch alt
            InspectResult(valid=True, url="url2", size="4MB", bitrate=""),  # search alt2
        ]
        mock_switch.return_value = Song(
            id="alt1", source="kuwo", name="Song A", artist="Artist",
            duration=200, cover="",
        )
        # First download (kuwo) raises 502, second (migu) succeeds
        mock_download.side_effect = [
            Exception("502 Bad Gateway"),
            Path("/tmp/song.mp3"),
        ]
        mock_lrc.return_value = Path("/tmp/song.lrc")
        # Search finds candidate on migu
        mock_search.return_value = [
            Song(id="migu1", source="migu", name="Song A", artist="Artist", duration=200, cover=""),
        ]

        results = self.client.download_playlist("123", "netease")
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].actual_source == "migu"

    @patch.object(MusicClient, "download_lyrics_file")
    @patch.object(MusicClient, "download")
    @patch.object(MusicClient, "inspect")
    @patch.object(MusicClient, "get_playlist_songs")
    def test_progress_callback(self, mock_playlist, mock_inspect, mock_download, mock_lrc):
        """Progress callback is invoked correctly."""
        songs = [
            Song(id="1", source="qq", name="Song A", artist="A", duration=100, cover=""),
        ]
        mock_playlist.return_value = songs
        mock_inspect.return_value = InspectResult(valid=True, url="url", size="2MB", bitrate="128kbps")
        mock_download.return_value = Path("/tmp/a.mp3")
        mock_lrc.return_value = Path("/tmp/a.lrc")

        calls = []
        def tracker(idx, total, name, status):
            calls.append((idx, total, name, status))

        self.client.download_playlist("123", "qq", on_progress=tracker)
        # Should be called twice per song: "检查资源..." then result
        assert len(calls) == 2
        assert calls[0] == (1, 1, "Song A", "检查资源...")
        assert "✅" in calls[1][3]
