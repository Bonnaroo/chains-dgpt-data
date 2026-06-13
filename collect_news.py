#!/usr/bin/env python3

"""
Chains - news fetcher.

Pulls headlines from public disc golf RSS feeds and saves them as data/news.json
for the app to read. Headlines + links only (we send readers to the source, we
never copy article bodies). No API key.

Usage:  python collect_news.py

Output: data/news.json
"""

import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

# Public RSS feeds explicitly published for app/reader consumption.
FEEDS = [
    {"source": "Ultiworld Disc Golf",
     "url": "https://discgolf.ultiworld.com/feed/all_excerpt/"},
]

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/rss+xml, application/xml, text/xml"}

MAX_ITEMS_PER_FEED = 15

def clean(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)            # strip any html tags
    text = (text.replace("&amp;", "&").replace("&#8217;", "'")
                .replace("&#8216;", "'").replace("&#8220;", '"')
                .replace("&#8221;", '"').replace("&#8211;", "-")
                .replace("&#8212;", "-").replace("&nbsp;", " ").replace("&quot;", '"'))
    return text.strip()

def fetch_feed(feed):
    req = urllib.request.Request(feed["url"], headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8", "replace")
    root = ET.fromstring(raw)
    items = []
    # RSS 2.0: channel/item with title, link, pubDate
    for item in root.iter("item"):
        title = clean(item.findtext("title"))
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        # skip the channel-level self-titles / empty
        if not title or not link or title.lower() == feed["source"].lower():
            continue
        items.append({
            "source": feed["source"],
            "title": title,
            "link": link,
            "published": pub,
        })
        if len(items) >= MAX_ITEMS_PER_FEED:
            break
    return items

def main():
    all_items = []
    for feed in FEEDS:
        try:
            got = fetch_feed(feed)
            print(f"  {feed['source']}: {len(got)} headlines")
            all_items.extend(got)
        except Exception as e:
            print(f"  {feed['source']}: ERROR {e}")

    out = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "note": "Headlines link to the original source. Tap to read there.",
        "items": all_items,
    }

    out_dir = Path("data")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "news.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"  saved data/news.json with {len(all_items)} headlines")

if __name__ == "__main__":
    main()
