#!/usr/bin/env python3
"""
Chains - highlights fetcher.
Pulls SHORT highlight-style videos (Top 5/10 shots, highlight reels, big-moment
clips) from disc golf channels via public RSS (no API key), filtered by title.
Saves data/highlights.json. Thumbnails + links point at YouTube; we never embed
or re-host (official channels block off-site playback, so we always link OUT).
Usage:  python collect_highlights.py
Output: data/highlights.json
"""

import json, re, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

CHANNELS = [
    {"name": "Disc Golf Pro Tour", "channel_id": "UCw0WzNn6m2Na6ZW7rKqWI3g"},
    {"name": "JomezPro",           "channel_id": "UCmGyCEbHfY91NFwHgioNLMQ"},
]

HEADERS = {"User-Agent": "Mozilla/5.0"}
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}

# Keep: highlight/short-form signals. Skip: full-round coverage.
KEEP = re.compile(r'highlight|top \d+|top shot|best shot|\bace\b|hole.?in.?one|'
                  r'must.?see|insane|nasty|erupt|recap|round.?up|🤏|🦖|🔥|😱', re.I)
SKIP = re.compile(r'rewatch|full round|r[123]f9|r[123]b9|finalf9|finalb9|'
                  r'\| f9 \||\| b9 \||round \d \|', re.I)

def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")

def fetch(ch):
    x = get(f"https://www.youtube.com/feeds/videos.xml?channel_id={ch['channel_id']}")
    root = ET.fromstring(x)
    out = []
    for e in root.findall("a:entry", NS):
        vid = e.findtext("yt:videoId", default="", namespaces=NS)
        title = e.findtext("a:title", default="", namespaces=NS).strip()
        pub = e.findtext("a:published", default="", namespaces=NS)
        if not vid or not title:
            continue
        if SKIP.search(title) or not KEEP.search(title):
            continue
        out.append({
            "channel": ch["name"],
            "title": title,
            "video_id": vid,
            "link": f"https://www.youtube.com/watch?v={vid}",
            "thumbnail": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
            "published": pub,
        })
    return out

def main():
    clips = []
    for ch in CHANNELS:
        try:
            got = fetch(ch)
            print(f"  {ch['name']}: {len(got)} highlights")
            clips.extend(got)
        except Exception as e:
            print(f"  {ch['name']}: ERROR {e}")
    clips.sort(key=lambda c: c.get("published", ""), reverse=True)
    out = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "note": "Short highlight clips. Tap to watch on YouTube.",
        "clips": clips,
    }
    Path("data").mkdir(parents=True, exist_ok=True)
    (Path("data") / "highlights.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"  saved data/highlights.json with {len(clips)} clips")

if __name__ == "__main__":
    main()
