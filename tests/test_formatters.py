"""Tests for Feishu card formatters and FeishuPusher."""

import sys
import os
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from music_toolkit import (
    Song,
    Playlist,
    FeishuPusher,
    _source_emoji,
    _format_song_table,
    _format_playlist_table,
    _format_lyrics_preview,
    _lrc_to_text,
)


# ─── Formatting Helper Tests ─────────────────────────────────────────────────

class TestSourceEmoji:
    def test_known_sources(self):
        assert _source_emoji("qq") == "🟢"
        assert _source_emoji("netease") == "🟣"
        assert _source_emoji("bilibili") == "🩷"

    def test_unknown_source(self):
        assert _source_emoji("unknown") == "🎵"


class TestFormatSongTable:
    def test_empty_list(self):
        assert "(无结果)" in _format_song_table([])

    def test_single_song(self):
        song = Song(
            id="1", source="qq", name="晴天", artist="周杰伦",
            duration=269, cover="", size="4.3 MB", bitrate="128kbps",
        )
        result = _format_song_table([song])
        assert "晴天" in result
        assert "周杰伦" in result
        assert "4:29" in result
        assert "[qq]" in result
        assert "4.3 MB" in result

    def test_multiple_songs(self):
        songs = [
            Song(id="1", source="qq", name="晴天", artist="周杰伦", duration=269, cover=""),
            Song(id="2", source="netease", name="稻香", artist="周杰伦", duration=223, cover=""),
        ]
        result = _format_song_table(songs)
        assert "1." in result
        assert "2." in result
        assert "晴天" in result
        assert "稻香" in result

    def test_no_index(self):
        songs = [Song(id="1", source="qq", name="晴天", artist="A", duration=0, cover="")]
        result = _format_song_table(songs, show_index=False)
        assert "1." not in result


class TestFormatPlaylistTable:
    def test_empty_list(self):
        assert "(无结果)" in _format_playlist_table([])

    def test_single_playlist(self):
        pl = Playlist(
            id="123", source="netease", name="周杰伦精选",
            cover="", track_count=50, creator="TestUser",
        )
        result = _format_playlist_table([pl])
        assert "周杰伦精选" in result
        assert "50 首" in result
        assert "TestUser" in result
        assert "[netease]" in result


# ─── FeishuPusher Tests (Mock feishu_toolkit) ────────────────────────────────

# Create a mock FeishuClient class for testing
def _create_mock_feishu_client():
    mock_cls = MagicMock()
    mock_instance = MagicMock()
    mock_cls.return_value = mock_instance

    # Card builder methods (static-like)
    mock_instance.card_fields.return_value = {"tag": "div", "fields": []}
    mock_instance.card_divider.return_value = {"tag": "hr"}
    mock_instance.card_markdown.return_value = {"tag": "div", "text": {"content": "", "tag": "lark_md"}}
    mock_instance.build_card.return_value = {
        "header": {"title": {"content": "Test"}},
        "elements": [],
    }
    mock_instance.send_card.return_value = {"code": 0, "data": {"message_id": "om_xxx"}}

    # Document methods
    mock_instance.heading_block.return_value = {"block_type": 3}
    mock_instance.text_block.return_value = {"block_type": 2}
    mock_instance.divider_block.return_value = {"block_type": 22}
    mock_instance.create_document_with_content.return_value = {
        "document_id": "doc_xxx",
        "url": "https://feishu.cn/docx/doc_xxx",
    }

    return mock_cls, mock_instance


class TestFeishuPusher:
    @patch("music_toolkit._import_feishu_client")
    def test_push_song_card(self, mock_import):
        mock_cls, mock_instance = _create_mock_feishu_client()
        mock_import.return_value = mock_cls

        pusher = FeishuPusher(
            app_id="test_id",
            app_secret="test_secret",
            default_chat_id="oc_test",
        )

        song = Song(
            id="abc", source="qq", name="晴天", artist="周杰伦",
            duration=269, cover="url", album="叶惠美",
            size="4.3 MB", bitrate="128kbps",
            lyrics="[00:30.42]故事的小黄花\n[00:33.97]从出生那年就飘着",
        )

        pusher.push_song_card(song)
        mock_instance.send_card.assert_called_once()
        call_args = mock_instance.send_card.call_args
        assert call_args[0][0] == "oc_test"  # chat_id

    @patch("music_toolkit._import_feishu_client")
    def test_push_song_card_custom_chat(self, mock_import):
        mock_cls, mock_instance = _create_mock_feishu_client()
        mock_import.return_value = mock_cls

        pusher = FeishuPusher(
            app_id="test_id",
            app_secret="test_secret",
            default_chat_id="oc_default",
        )

        song = Song(id="abc", source="qq", name="Test", artist="A", duration=0, cover="")
        pusher.push_song_card(song, chat_id="oc_custom")
        call_args = mock_instance.send_card.call_args
        assert call_args[0][0] == "oc_custom"

    @patch("music_toolkit._import_feishu_client")
    def test_push_search_results(self, mock_import):
        mock_cls, mock_instance = _create_mock_feishu_client()
        mock_import.return_value = mock_cls

        pusher = FeishuPusher(
            app_id="test_id",
            app_secret="test_secret",
            default_chat_id="oc_test",
        )

        songs = [
            Song(id=str(i), source="qq", name=f"Song {i}", artist="A", duration=100 * i, cover="")
            for i in range(1, 4)
        ]

        pusher.push_search_results(songs, "test keyword")
        mock_instance.send_card.assert_called_once()

    @patch("music_toolkit._import_feishu_client")
    def test_push_playlist_card(self, mock_import):
        mock_cls, mock_instance = _create_mock_feishu_client()
        mock_import.return_value = mock_cls

        pusher = FeishuPusher(
            app_id="test_id",
            app_secret="test_secret",
            default_chat_id="oc_test",
        )

        playlist = Playlist(
            id="123", source="netease", name="周杰伦精选",
            cover="", track_count=50, creator="User",
        )
        songs = [
            Song(id="1", source="netease", name="晴天", artist="周杰伦", duration=269, cover=""),
        ]

        pusher.push_playlist_card(playlist, songs=songs)
        mock_instance.send_card.assert_called_once()

    @patch("music_toolkit._import_feishu_client")
    def test_create_song_document(self, mock_import):
        mock_cls, mock_instance = _create_mock_feishu_client()
        mock_import.return_value = mock_cls

        pusher = FeishuPusher(
            app_id="test_id",
            app_secret="test_secret",
            default_chat_id="oc_test",
        )

        song = Song(
            id="abc", source="qq", name="晴天", artist="周杰伦",
            duration=269, cover="", album="叶惠美",
            lyrics="[00:30.42]故事的小黄花",
        )

        url = pusher.create_song_document(song)
        assert "feishu.cn" in url
        mock_instance.create_document_with_content.assert_called_once()

    @patch("music_toolkit._import_feishu_client")
    def test_missing_chat_id(self, mock_import):
        mock_cls, mock_instance = _create_mock_feishu_client()
        mock_import.return_value = mock_cls

        pusher = FeishuPusher(
            app_id="test_id",
            app_secret="test_secret",
            default_chat_id="",
        )

        song = Song(id="abc", source="qq", name="Test", artist="A", duration=0, cover="")
        with pytest.raises(ValueError, match="chat_id"):
            pusher.push_song_card(song)

    @patch("music_toolkit._import_feishu_client")
    def test_push_song_card_no_lyrics(self, mock_import):
        mock_cls, mock_instance = _create_mock_feishu_client()
        mock_import.return_value = mock_cls

        pusher = FeishuPusher(
            app_id="test_id",
            app_secret="test_secret",
            default_chat_id="oc_test",
        )

        song = Song(id="abc", source="qq", name="Test", artist="A", duration=100, cover="")
        pusher.push_song_card(song)
        # Should not call card_divider when no lyrics
        # (card_divider is only added when lyrics exist)
        mock_instance.send_card.assert_called_once()

    @patch("music_toolkit._import_feishu_client")
    def test_push_search_results_over_10(self, mock_import):
        mock_cls, mock_instance = _create_mock_feishu_client()
        mock_import.return_value = mock_cls

        pusher = FeishuPusher(
            app_id="test_id",
            app_secret="test_secret",
            default_chat_id="oc_test",
        )

        songs = [
            Song(id=str(i), source="qq", name=f"Song {i}", artist="A", duration=100, cover="")
            for i in range(15)
        ]

        pusher.push_search_results(songs, "test")
        # Should include "共 15 首" in the card
        mock_instance.card_markdown.assert_called()
        call_arg = mock_instance.card_markdown.call_args[0][0]
        assert "15" in call_arg


# ─── LRC to Text Formatting Tests ──────────────────────────────────────────

class TestLrcToTextFormatting:
    def test_preserves_content(self):
        """Ensure _lrc_to_text preserves song lyrics content."""
        lrc = "[00:30.42]故事的小黄花\n[00:33.97]从出生那年就飘着\n[00:37.62]童年的荡秋千"
        text = _lrc_to_text(lrc)
        assert "故事的小黄花" in text
        assert "从出生那年就飘着" in text
        assert "童年的荡秋千" in text

    def test_no_time_tags_in_output(self):
        lrc = "[00:30.42]Line A\n[01:00.00]Line B"
        text = _lrc_to_text(lrc)
        assert "[00:" not in text
        assert "[01:" not in text

    def test_metadata_stripped(self):
        lrc = "[ti:Song Title]\n[ar:Artist]\n[00:30.42]Content"
        text = _lrc_to_text(lrc)
        assert "Content" in text
        assert "Song Title" not in text
        assert "Artist" not in text


# ─── Song Table with Album Tests ────────────────────────────────────────────

class TestFormatSongTableWithAlbum:
    def test_song_with_album_shows_source(self):
        """Even with album, format_song_table should show source tag."""
        song = Song(
            id="1", source="netease", name="拥有", artist="李泉",
            duration=273, cover="", album="再见忧伤",
        )
        result = _format_song_table([song])
        assert "拥有" in result
        assert "李泉" in result
        assert "[netease]" in result


# ─── FeishuPusher send_song_files Tests ──────────────────────────────────────

class TestSendSongFiles:
    @patch("music_toolkit._import_feishu_client")
    def test_single_file(self, mock_import, tmp_path):
        """Single file should be uploaded directly (no zip)."""
        mock_cls, mock_instance = _create_mock_feishu_client()
        mock_instance.upload_file.return_value = "file_v2_abc"
        mock_instance.send_file.return_value = {"code": 0, "data": {"message_id": "om_xxx"}}
        mock_import.return_value = mock_cls

        pusher = FeishuPusher(
            app_id="test_id", app_secret="test_secret",
            default_chat_id="oc_test",
        )

        # Create a fake file
        song_file = tmp_path / "test.mp3"
        song_file.write_bytes(b"fake audio data")

        result = pusher.send_song_files([song_file])
        assert result["code"] == 0
        mock_instance.upload_file.assert_called_once_with(str(song_file))
        mock_instance.send_file.assert_called_once_with("oc_test", "file_v2_abc")

    @patch("music_toolkit._import_feishu_client")
    def test_multiple_files_zip(self, mock_import, tmp_path):
        """Multiple files should be zipped before upload."""
        mock_cls, mock_instance = _create_mock_feishu_client()
        mock_instance.upload_file.return_value = "file_v2_zip"
        mock_instance.send_file.return_value = {"code": 0}
        mock_import.return_value = mock_cls

        pusher = FeishuPusher(
            app_id="test_id", app_secret="test_secret",
            default_chat_id="oc_test",
        )

        # Create multiple fake files
        files = []
        for name in ["song1.mp3", "song2.mp3", "song1.lrc"]:
            f = tmp_path / name
            f.write_bytes(b"fake data")
            files.append(f)

        pusher.send_song_files(files, zip_name="test_songs")
        mock_instance.upload_file.assert_called_once()
        # Verify the uploaded file is a zip
        uploaded_path = mock_instance.upload_file.call_args[0][0]
        assert uploaded_path.endswith(".zip")

    @patch("music_toolkit._import_feishu_client")
    def test_custom_chat_id(self, mock_import, tmp_path):
        """Custom chat_id should override default."""
        mock_cls, mock_instance = _create_mock_feishu_client()
        mock_instance.upload_file.return_value = "file_v2_abc"
        mock_instance.send_file.return_value = {"code": 0}
        mock_import.return_value = mock_cls

        pusher = FeishuPusher(
            app_id="test_id", app_secret="test_secret",
            default_chat_id="oc_default",
        )

        song_file = tmp_path / "test.mp3"
        song_file.write_bytes(b"data")

        pusher.send_song_files([song_file], chat_id="oc_custom")
        mock_instance.send_file.assert_called_once_with("oc_custom", "file_v2_abc")

    @patch("music_toolkit._import_feishu_client")
    def test_empty_list_raises(self, mock_import):
        """Empty file list should raise ValueError."""
        mock_cls, _ = _create_mock_feishu_client()
        mock_import.return_value = mock_cls

        pusher = FeishuPusher(
            app_id="test_id", app_secret="test_secret",
            default_chat_id="oc_test",
        )

        with pytest.raises(ValueError, match="不能为空"):
            pusher.send_song_files([])

    @patch("music_toolkit._import_feishu_client")
    def test_nonexistent_files_raises(self, mock_import):
        """All nonexistent files should raise FileNotFoundError."""
        mock_cls, _ = _create_mock_feishu_client()
        mock_import.return_value = mock_cls

        pusher = FeishuPusher(
            app_id="test_id", app_secret="test_secret",
            default_chat_id="oc_test",
        )

        from pathlib import Path
        with pytest.raises(FileNotFoundError, match="均不存在"):
            pusher.send_song_files([Path("/nonexistent/file.mp3")])

    @patch("music_toolkit._import_feishu_client")
    def test_skips_missing_files(self, mock_import, tmp_path):
        """Should skip nonexistent files but process existing ones."""
        mock_cls, mock_instance = _create_mock_feishu_client()
        mock_instance.upload_file.return_value = "file_v2_abc"
        mock_instance.send_file.return_value = {"code": 0}
        mock_import.return_value = mock_cls

        pusher = FeishuPusher(
            app_id="test_id", app_secret="test_secret",
            default_chat_id="oc_test",
        )

        existing = tmp_path / "exists.mp3"
        existing.write_bytes(b"data")
        missing = tmp_path / "missing.mp3"

        # 1 existing + 1 missing = single file, direct upload
        pusher.send_song_files([existing, missing])
        mock_instance.upload_file.assert_called_once_with(str(existing))

