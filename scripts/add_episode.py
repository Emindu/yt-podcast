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


def download_audio(url: str) -> tuple:
    tmp = Path(tempfile.mkdtemp())
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
        "extractor_args": {"youtube": {"player_client": ["ios"]}},
        "quiet": True,
        "no_warnings": True,
    }
    cookies_file = os.environ.get("COOKIES_FILE")
    if cookies_file and Path(cookies_file).exists():
        ydl_opts["cookiefile"] = cookies_file
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    mp3_path = tmp / f"{info['id']}.mp3"
    return info, mp3_path


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


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/add_episode.py <youtube_url>")
        sys.exit(1)

    url = sys.argv[1]
    print(f"Downloading audio from: {url}")
    info, mp3_path = download_audio(url)

    video_id = info["id"]
    title = info.get("title", "Unknown")
    filename = f"{video_id}.mp3"
    print(f"Downloaded: {title}")

    release = get_or_create_release(video_id, title)
    audio_url = upload_asset(release, mp3_path, filename)
    print(f"Audio URL: {audio_url}")

    episodes_file = Path("data/episodes.json")
    episodes = load_episodes()

    if any(e["id"] == video_id for e in episodes):
        print(f"Episode {video_id} already in feed. Skipping.")
        sys.exit(0)

    episodes.insert(
        0,
        {
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
        },
    )
    episodes_file.write_text(json.dumps(episodes, indent=2))
    print(f"episodes.json updated ({len(episodes)} episodes)")

    pages_base_url = get_pages_base_url()
    generate_feed(episodes, pages_base_url)
    print(f"Done! Episode added: {title}")
    print(f"Feed URL: {pages_base_url}/feed.xml")


if __name__ == "__main__":
    main()
