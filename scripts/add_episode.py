#!/usr/bin/env python3
"""
Downloads a YouTube video as MP3, uploads it to a GitHub Release,
updates data/episodes.json, and regenerates docs/feed.xml.

Usage:
    python scripts/add_episode.py <youtube_url>

Required env vars:
    GITHUB_TOKEN  - token with contents:write permission
    REPO          - owner/repo-name
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path

import requests
import yt_dlp

sys.path.insert(0, str(Path(__file__).parent.parent))
from feed import generate_feed, load_episodes

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
REPO = os.environ["REPO"]
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}
API = "https://api.github.com"


def get_pages_base_url() -> str:
    owner, repo_name = REPO.split("/")
    return f"https://{owner}.github.io/{repo_name}"


DOWNLOAD_RETRIES = 3
DOWNLOAD_RETRY_DELAY = 10  # seconds


def build_ydl_opts(tmp: Path) -> dict:
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(tmp / "%(id)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "remote_components": "ejs:github",
        "extractor_retries": 3,
        "fragment_retries": 3,
        "quiet": True,
        "no_warnings": True,
    }
    cookies_file = os.environ.get("COOKIES_FILE")
    if cookies_file and Path(cookies_file).exists() and Path(cookies_file).stat().st_size > 0:
        ydl_opts["cookiefile"] = cookies_file
    else:
        print(
            "WARNING: no usable cookies file found (COOKIES_FILE unset, missing, "
            "or empty). YouTube is likely to block the download with a "
            "'Sign in to confirm you’re not a bot' error. Refresh the "
            "YOUTUBE_COOKIES secret with a fresh export from a logged-in browser."
        )
    return ydl_opts


def download_audio(url: str) -> tuple:
    tmp = Path(tempfile.mkdtemp())
    ydl_opts = build_ydl_opts(tmp)

    last_error = None
    for attempt in range(1, DOWNLOAD_RETRIES + 1):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
            mp3_path = tmp / f"{info['id']}.mp3"
            return info, mp3_path
        except yt_dlp.utils.DownloadError as e:
            last_error = e
            if attempt < DOWNLOAD_RETRIES:
                print(
                    f"Download attempt {attempt}/{DOWNLOAD_RETRIES} failed "
                    f"({e}); retrying in {DOWNLOAD_RETRY_DELAY}s..."
                )
                time.sleep(DOWNLOAD_RETRY_DELAY)

    raise last_error


def download_playlist(playlist_url: str):
    """Downloads every video in a playlist using a single yt-dlp session
    (exactly the same download options as a single-video download), and
    yields (info, mp3_path) for each video in playlist order.
    """
    tmp = Path(tempfile.mkdtemp())
    ydl_opts = build_ydl_opts(tmp)
    ydl_opts["ignoreerrors"] = True

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        playlist_info = ydl.extract_info(playlist_url, download=True)

    entries = playlist_info.get("entries") or [playlist_info]
    for entry in entries:
        if not entry:
            continue
        mp3_path = tmp / f"{entry['id']}.mp3"
        if mp3_path.exists():
            yield entry, mp3_path
        else:
            print(f"Skipping {entry.get('id')}: no audio file produced (download failed).")


def get_or_create_release(video_id: str, title: str) -> dict:
    r = requests.get(f"{API}/repos/{REPO}/releases/tags/{video_id}", headers=HEADERS)
    if r.status_code == 200:
        print(f"Release already exists for {video_id}, reusing.")
        return r.json()

    r = requests.post(
        f"{API}/repos/{REPO}/releases",
        headers=HEADERS,
        json={
            "tag_name": video_id,
            "name": title,
            "body": f"Podcast episode audio for: {title}",
            "draft": False,
            "prerelease": False,
        },
    )
    r.raise_for_status()
    return r.json()


def upload_asset(release: dict, mp3_path: Path, filename: str) -> str:
    # Check if asset already uploaded
    for asset in release.get("assets", []):
        if asset["name"] == filename:
            print(f"Asset {filename} already uploaded.")
            return asset["browser_download_url"]

    upload_url = release["upload_url"].replace("{?name,label}", "")
    print(f"Uploading {filename} ({mp3_path.stat().st_size // 1024 // 1024} MB)...")
    with open(mp3_path, "rb") as f:
        r = requests.post(
            upload_url,
            headers={**HEADERS, "Content-Type": "audio/mpeg"},
            params={"name": filename},
            data=f,
        )
    r.raise_for_status()
    return r.json()["browser_download_url"]


def upload_episode(info: dict, mp3_path: Path, episodes: list) -> dict | None:
    """Uploads an already-downloaded video and prepends its episode entry
    to `episodes`. Returns the new episode dict, or None if it was already
    present.
    """
    video_id = info["id"]
    title = info.get("title", "Unknown")
    filename = f"{video_id}.mp3"

    if any(e["id"] == video_id for e in episodes):
        print(f"Episode {video_id} already in feed. Skipping.")
        return None

    release = get_or_create_release(video_id, title)
    audio_url = upload_asset(release, mp3_path, filename)
    print(f"Audio URL: {audio_url}")

    episode = {
        "id": video_id,
        "title": title,
        "description": info.get("description", ""),
        "duration": info.get("duration", 0),
        "filename": filename,
        "audio_url": audio_url,
        "thumbnail": info.get("thumbnail", ""),
        "uploader": info.get("uploader", "Unknown"),
        "upload_date": info.get("upload_date", ""),
        "file_size": mp3_path.stat().st_size,
    }
    episodes.insert(0, episode)
    return episode


def add_episode_to_list(url: str, episodes: list) -> dict | None:
    """Downloads a single video and prepends its episode entry to `episodes`.

    Returns the new episode dict, or None if it was already present.
    """
    print(f"Downloading audio from: {url}")
    info, mp3_path = download_audio(url)
    title = info.get("title", "Unknown")
    print(f"Downloaded: {title}")
    return upload_episode(info, mp3_path, episodes)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/add_episode.py <youtube_url>")
        sys.exit(1)

    url = sys.argv[1]
    episodes = load_episodes()
    episode = add_episode_to_list(url, episodes)

    if episode is None:
        sys.exit(0)

    Path("data/episodes.json").write_text(json.dumps(episodes, indent=2))
    print(f"episodes.json updated ({len(episodes)} episodes)")

    pages_base_url = get_pages_base_url()
    generate_feed(episodes, pages_base_url)
    print(f"Done! Episode added: {episode['title']}")
    print(f"Feed URL: {pages_base_url}/feed.xml")


if __name__ == "__main__":
    main()
