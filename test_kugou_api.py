#!/usr/bin/env python3
"""
测试 KuGouMusicApi 集成

用法:
    python3 test_kugou_api.py
"""

import os
import sys
import requests

# 测试配置
KUGOU_API_URL = os.environ.get("KUGOU_API_URL", "http://localhost:3000")
TEST_PLAYLIST_URL = "https://www.kugou.com/songlist/gcid_1863870844/"
TEST_COLLECTION_ID = "collection_3_1863870844_4_0"


def test_api_health():
    """测试 KuGouMusicApi 服务是否可用"""
    print("🔍 测试 KuGouMusicApi 服务健康状态...")
    try:
        resp = requests.get(f"{KUGOU_API_URL}/", timeout=5)
        if resp.status_code == 200:
            print(f"✅ KuGouMusicApi 服务正常运行 ({KUGOU_API_URL})")
            return True
        else:
            print(f"❌ KuGouMusicApi 返回异常状态码: {resp.status_code}")
            return False
    except requests.RequestException as e:
        print(f"❌ 无法连接到 KuGouMusicApi: {e}")
        print(f"   请确保服务已启动: docker-compose -f docker-compose.kugou-api.yml up -d")
        return False


def test_playlist_detail():
    """测试歌单详情接口"""
    print(f"\n🔍 测试歌单详情接口...")
    print(f"   Collection ID: {TEST_COLLECTION_ID}")

    try:
        resp = requests.get(
            f"{KUGOU_API_URL}/playlist/detail",
            params={"ids": TEST_COLLECTION_ID},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 200:
            print(f"❌ API 返回错误: {data}")
            return False

        playlist = data["data"][0] if isinstance(data["data"], list) else data["data"]
        print(f"✅ 歌单详情获取成功:")
        print(f"   标题: {playlist.get('name', 'N/A')}")
        print(f"   创建者: {playlist.get('username', 'N/A')}")
        print(f"   播放量: {playlist.get('playcount', 0):,}")
        print(f"   收藏量: {playlist.get('collectcount', 0):,}")
        return True

    except Exception as e:
        print(f"❌ 歌单详情接口测试失败: {e}")
        return False


def test_playlist_tracks():
    """测试歌单歌曲列表接口"""
    print(f"\n🔍 测试歌单歌曲列表接口...")

    try:
        resp = requests.get(
            f"{KUGOU_API_URL}/playlist/track/all",
            params={"id": TEST_COLLECTION_ID, "page": 1, "pagesize": 10},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 200:
            print(f"❌ API 返回错误: {data}")
            return False

        songs = data.get("data", {}).get("info", [])
        total = data.get("data", {}).get("total", 0)

        print(f"✅ 歌曲列表获取成功:")
        print(f"   总歌曲数: {total}")
        print(f"   本页歌曲数: {len(songs)}")

        if songs:
            print(f"\n   前 3 首歌曲:")
            for i, song in enumerate(songs[:3], 1):
                filename = song.get("filename", "")
                duration = song.get("duration", 0)
                print(f"   {i}. {filename} ({duration}s)")

        return True

    except Exception as e:
        print(f"❌ 歌曲列表接口测试失败: {e}")
        return False


def test_music_toolkit_integration():
    """测试 music_toolkit.py 集成"""
    print(f"\n🔍 测试 music_toolkit.py 集成...")

    try:
        # 导入 music_toolkit
        sys.path.insert(0, os.path.dirname(__file__))
        from music_toolkit import _fetch_kugou_playlist_via_api

        print(f"   正在获取歌单: {TEST_COLLECTION_ID}")
        playlist = _fetch_kugou_playlist_via_api(TEST_COLLECTION_ID, timeout=15)

        print(f"✅ music_toolkit 集成成功:")
        print(f"   歌单标题: {playlist.title}")
        print(f"   创建者: {playlist.creator}")
        print(f"   歌曲数量: {playlist.track_count}")
        print(f"   实际获取: {len(playlist.tracks)} 首")

        if playlist.tracks:
            print(f"\n   前 3 首歌曲:")
            for i, track in enumerate(playlist.tracks[:3], 1):
                print(f"   {i}. {track.name} - {track.artist}")

        return True

    except Exception as e:
        print(f"❌ music_toolkit 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("KuGouMusicApi 集成测试")
    print("=" * 60)

    results = []

    # 测试 1: 服务健康检查
    results.append(("服务健康检查", test_api_health()))

    if not results[0][1]:
        print("\n⚠️  KuGouMusicApi 服务未运行，跳过后续测试")
        print("   启动命令: docker-compose -f docker-compose.kugou-api.yml up -d")
        return 1

    # 测试 2: 歌单详情接口
    results.append(("歌单详情接口", test_playlist_detail()))

    # 测试 3: 歌单歌曲列表接口
    results.append(("歌单歌曲列表接口", test_playlist_tracks()))

    # 测试 4: music_toolkit 集成
    results.append(("music_toolkit 集成", test_music_toolkit_integration()))

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {name}")

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    print(f"\n总计: {passed_count}/{total_count} 通过")

    return 0 if passed_count == total_count else 1


if __name__ == "__main__":
    sys.exit(main())
