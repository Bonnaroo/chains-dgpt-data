#!/usr/bin/env python3
"""
Chains - player channel fetcher.
Pulls latest videos from pro players' personal YouTube channels (practice
rounds, vlogs, battles) via public RSS (no API key). Saves data/players_videos.json.
A casual "latest from the guys" feed. Thumbnails + links point at YouTube; we
never embed or re-host. To add a player, drop their channel_id in CHANNELS.
Usage:  python collect_players.py
Output: data/players_videos.json
"""

import json, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

CHANNELS = [
    {"name": "Aaron Gossage",  "channel_id": "UCnTnv0pSDJjZRQlppkp0qUg"},
    {"name": "Ezra Aderhold",  "channel_id": "UCJ5qQfW0IPRGunN3hIrrKKA"},
]

HEADERS = {"User-Agent": "Mozilla/5.0"}
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
PER_CHANNEL = 8

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
        out.append({
            "player": ch["name"],
            "title": title,
            "video_id": vid,
            "link": f"https://www.youtube.com/watch?v={vid}",
            "thumbnail": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
            "published": pub,
        })
        if len(out) >= PER_CHANNEL:
            break
    return out

def main():
    vids = []
    for ch in CHANNELS:
        try:
            got = fetch(ch)
            print(f"  {ch['name']}: {len(got)} videos")
            vids.extend(got)
        except Exception as e:
            print(f"  {ch['name']}: ERROR {e}")
    vids.sort(key=lambda v: v.get("published", ""), reverse=True)
    out = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "note": "Latest from pro players' own channels. Tap to watch on YouTube.",
        "videos": vids,
    }
    Path("data").mkdir(parents=True, exist_ok=True)
    (Path("data") / "players_videos.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"  saved data/players_videos.json with {len(vids)} videos")

if __name__ == "__main__":
    main()
