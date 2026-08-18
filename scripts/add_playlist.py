#!/usr/bin/env python3
"""
Downloads every video in a YouTube playlist as MP3 episodes, uploads them
to GitHub Releases, updates data/episodes.json, and regenerates docs/feed.xml.

This reuses the exact same yt-dlp download logic as add_episode.py
(scripts/add_episode.py:download_playlist), just pointed at the playlist
URL directly so yt-dlp downloads the whole playlist in one session -
matching how a single video download already works.

Usage:
    python scripts/add_playlist.py <playlist_url_or_id>

Required env vars:
    GITHUB_TOKEN  - token with contents:write permission
    REPO          - owner/repo-name
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feed import generate_feed, load_episodes
from add_episode import download_playlist, upload_episode, get_pages_base_url

EPISODES_FILE = Path("data/episodes.json")


def resolve_playlist_url(playlist_url_or_id: str) -> str:
    if playlist_url_or_id.startswith("http"):
        return playlist_url_or_id
    return f"https://www.youtube.com/playlist?list={playlist_url_or_id}"


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/add_playlist.py <playlist_url_or_id>")
        sys.exit(1)

    playlist_url = resolve_playlist_url(sys.argv[1])
    print(f"Downloading playlist: {playlist_url}")

    episodes = load_episodes()
    added = 0

    for info, mp3_path in download_playlist(playlist_url):
        title = info.get("title", "Unknown")
        print(f"\nDownloaded: {title}")
        episode = upload_episode(info, mp3_path, episodes)
        if episode is not None:
            added += 1
            EPISODES_FILE.write_text(json.dumps(episodes, indent=2))

    pages_base_url = get_pages_base_url()
    generate_feed(episodes, pages_base_url)

    print(f"\nDone! Added {added} new episode(s) from playlist.")
    print(f"Feed URL: {pages_base_url}/feed.xml")


if __name__ == "__main__":
    main()
