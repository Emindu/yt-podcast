#!/usr/bin/env python3
"""
Removes an episode from data/episodes.json, deletes its GitHub Release,
and regenerates docs/feed.xml.

Usage:
    python scripts/delete_episode.py <video_id>

Required env vars:
    GITHUB_TOKEN  - token with contents:write permission
    REPO          - owner/repo-name
"""

import json
import os
import sys
from pathlib import Path

import requests

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


def delete_release(video_id: str):
    r = requests.get(f"{API}/repos/{REPO}/releases/tags/{video_id}", headers=HEADERS)
    if r.status_code == 404:
        print(f"No release found for {video_id}, skipping.")
        return

    release_id = r.json()["id"]
    r = requests.delete(f"{API}/repos/{REPO}/releases/{release_id}", headers=HEADERS)
    r.raise_for_status()

    # Also delete the git tag
    r = requests.delete(f"{API}/repos/{REPO}/git/refs/tags/{video_id}", headers=HEADERS)
    if r.status_code not in (204, 422):
        r.raise_for_status()

    print(f"Deleted release and tag for {video_id}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/delete_episode.py <video_id>")
        sys.exit(1)

    video_id = sys.argv[1]
    episodes = load_episodes()
    updated = [e for e in episodes if e["id"] != video_id]

    if len(updated) == len(episodes):
        print(f"Episode {video_id} not found in episodes.json")
        sys.exit(1)

    removed = next(e for e in episodes if e["id"] == video_id)
    print(f"Removing: {removed['title']}")

    Path("data/episodes.json").write_text(json.dumps(updated, indent=2))
    delete_release(video_id)

    pages_base_url = get_pages_base_url()
    generate_feed(updated, pages_base_url)
    print(f"Done! Episode removed: {removed['title']}")


if __name__ == "__main__":
    main()
