#!/usr/bin/env python3
"""
Downloads every video in a YouTube playlist as MP3 episodes, uploads them
to GitHub Releases, updates data/episodes.json, and regenerates docs/feed.xml.

Usage:
    python scripts/add_playlist.py <playlist_url_or_id>

Required env vars:
    GITHUB_TOKEN  - token with contents:write permission
    REPO          - owner/repo-name
"""

import os
import sys
import json
from pathlib import Path

import yt_dlp

sys.path.insert(0, str(Path(__file__).parent.parent))
from feed import generate_feed, load_episodes
from add_episode import add_episode_to_list, get_pages_base_url

EPISODES_FILE = Path("data/episodes.json")


def resolve_playlist_url(playlist_url_or_id: str) -> str:
    if playlist_url_or_id.startswith("http"):
        return playlist_url_or_id
    return f"https://www.youtube.com/playlist?list={playlist_url_or_id}"


def list_video_urls(playlist_url: str) -> list:
    ydl_opts = {
        "extract_flat": True,
        "quiet": True,
        "no_warnings": True,
    }
    cookies_file = os.environ.get("COOKIES_FILE")
    if cookies_file and Path(cookies_file).exists():
        ydl_opts["cookiefile"] = cookies_file
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)

    entries = info.get("entries") or []
    urls = []
    for entry in entries:
        if not entry:
            continue
        video_id = entry.get("id")
        if video_id:
            urls.append(f"https://www.youtube.com/watch?v={video_id}")
    return urls


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/add_playlist.py <playlist_url_or_id>")
        sys.exit(1)

    playlist_url = resolve_playlist_url(sys.argv[1])
    print(f"Fetching playlist: {playlist_url}")
    video_urls = list_video_urls(playlist_url)
    print(f"Found {len(video_urls)} videos in playlist")

    if not video_urls:
        print("No videos found in playlist.")
        sys.exit(1)

    episodes = load_episodes()
    added = 0
    failed = []

    for i, url in enumerate(video_urls, start=1):
        print(f"\n[{i}/{len(video_urls)}] Processing {url}")
        try:
            episode = add_episode_to_list(url, episodes)
            if episode is not None:
                added += 1
                EPISODES_FILE.write_text(json.dumps(episodes, indent=2))
        except Exception as e:
            print(f"Failed to process {url}: {e}")
            failed.append(url)

    pages_base_url = get_pages_base_url()
    generate_feed(episodes, pages_base_url)

    print(f"\nDone! Added {added} new episode(s) from playlist.")
    if failed:
        print(f"Failed to process {len(failed)} video(s):")
        for url in failed:
            print(f"  - {url}")
    print(f"Feed URL: {pages_base_url}/feed.xml")


if __name__ == "__main__":
    main()
