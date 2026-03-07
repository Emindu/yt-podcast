import json
from pathlib import Path
from datetime import datetime, timezone

from feedgen.feed import FeedGenerator

EPISODES_FILE = Path("data/episodes.json")
FEED_FILE = Path("docs/feed.xml")
CONFIG_FILE = Path("podcast.json")


def load_config() -> dict:
    return json.loads(CONFIG_FILE.read_text())


def load_episodes() -> list:
    if EPISODES_FILE.exists():
        return json.loads(EPISODES_FILE.read_text())
    return []


def generate_feed(episodes: list, base_url: str):
    config = load_config()

    fg = FeedGenerator()
    fg.load_extension("podcast")

    fg.id(f"{base_url}/feed.xml")
    fg.title(config["title"])
    fg.description(config["description"])
    fg.author({"name": config["author"], "email": config["email"]})
    fg.link(href=f"{base_url}/feed.xml", rel="self")
    fg.language("en")
    fg.podcast.itunes_author(config["author"])
    fg.podcast.itunes_explicit("no")

    for ep in episodes:
        fe = fg.add_entry()
        fe.id(ep["audio_url"])
        fe.title(ep["title"])
        fe.description(ep.get("description", "")[:1000] or ep["title"])
        fe.enclosure(
            url=ep["audio_url"],
            length=str(ep.get("file_size", 0)),
            type="audio/mpeg",
        )
        fe.podcast.itunes_duration(ep.get("duration", 0))
        fe.podcast.itunes_author(ep.get("uploader", config["author"]))

        upload_date = ep.get("upload_date", "")
        if upload_date:
            pub_date = datetime.strptime(upload_date, "%Y%m%d").replace(tzinfo=timezone.utc)
        else:
            pub_date = datetime.now(timezone.utc)
        fe.pubDate(pub_date)

    FEED_FILE.parent.mkdir(exist_ok=True)
    fg.rss_file(str(FEED_FILE))
    print(f"Feed written to {FEED_FILE}")
