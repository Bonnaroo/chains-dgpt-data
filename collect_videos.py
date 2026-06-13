#!/usr/bin/env python3

"""
Chains - video fetcher.

Pulls the latest videos from disc golf YouTube channels via their public RSS
feeds (no API key) and saves data/videos.json for the app. We store the video
title, link, channel, published date, and the official YouTube thumbnail URL.

The app shows thumbnails that LINK OUT to YouTube -- we never re-host video or
images, we point at YouTube's own.

Usage:  python collect_videos.py

Output: data/videos.json
"""

import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

# Public YouTube channel RSS feeds (no API key needed).
CHANNELS = [
    {"name": "JomezPro",          "channel_id": "UCmGyCEbHfY91NFwHgioNLMQ"},
    {"name": "Disc Golf Network", "channel_id": "UCKw8iyzuymljxkzu7HdZ1zA"},
    {"name": "Gatekeeper Media",  "channel_id": "UC9a1V9evArQaHOlkqeY63Iw"},
    {"name": "Disc Golf Pro Tour","channel_id": "UCw0WzNn6m2Na6ZW7rKqWI3g"},
]

HEADERS = {"User-Agent": "Mozilla/5.0"}
PER_CHANNEL = 6
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015",
      "media": "http://search.yahoo.com/mrss/"}

def fetch_channel(ch):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={ch['channel_id']}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8", "replace")
    root = ET.fromstring(raw)
    out = []
    for entry in root.findall("a:entry", NS):
        vid = entry.findtext("yt:videoId", default="", namespaces=NS)
        title = entry.findtext("a:title", default="", namespaces=NS)
        published = entry.findtext("a:published", default="", namespaces=NS)
        if not vid or not title:
            continue
        out.append({
            "channel": ch["name"],
            "title": title.strip(),
            "video_id": vid,
            "link": f"https://www.youtube.com/watch?v={vid}",
            "thumbnail": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
            "published": published,
        })
        if len(out) >= PER_CHANNEL:
            break
    return out

def main():
    all_videos = []
    for ch in CHANNELS:
        try:
            got = fetch_channel(ch)
            print(f"  {ch['name']}: {len(got)} videos")
            all_videos.extend(got)
        except Exception as e:
            print(f"  {ch['name']}: ERROR {e}")

    # newest first across all channels (published is ISO-ish, sortable as string)
    all_videos.sort(key=lambda v: v.get("published", ""), reverse=True)

    out = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "note": "Thumbnails and titles link to YouTube. Tap to watch there.",
        "videos": all_videos,
    }

    Path("data").mkdir(parents=True, exist_ok=True)
    (Path("data") / "videos.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"  saved data/videos.json with {len(all_videos)} videos")

if __name__ == "__main__":
    main()
