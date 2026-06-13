#!/usr/bin/env python3
"""
Chains - video fetcher (Jomez, organized by tournament).
Pulls Jomez Pro's per-tournament playlists via public RSS (no API key) and saves
data/videos.json grouped by tournament, each with its round videos in order.
Thumbnails + links point at YouTube; we never re-host anything.
Usage:  python collect_videos.py
Output: data/videos.json
"""

import json, re, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

JOMEZ_PLAYLISTS_URL = "https://www.youtube.com/@JomezPro/playlists"
HEADERS = {"User-Agent": "Mozilla/5.0"}
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}

def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")

def fetch_playlist(pid):
    x = get(f"https://www.youtube.com/feeds/videos.xml?playlist_id={pid}")
    root = ET.fromstring(x)
    pl_title = root.findtext("a:title", default="", namespaces=NS).strip()
    vids = []
    for entry in root.findall("a:entry", NS):
        vid = entry.findtext("yt:videoId", default="", namespaces=NS)
        title = entry.findtext("a:title", default="", namespaces=NS).strip()
        published = entry.findtext("a:published", default="", namespaces=NS)
        if not vid:
            continue
        vids.append({
            "title": title,
            "video_id": vid,
            "link": f"https://www.youtube.com/watch?v={vid}",
            "thumbnail": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
            "published": published,
        })
    return pl_title, vids

def main():
    html = get(JOMEZ_PLAYLISTS_URL)
    ids = list(dict.fromkeys(re.findall(r'"playlistId":"(PL[^"]+)"', html)))
    tournaments = []
    for pid in ids[:40]:
        try:
            title, vids = fetch_playlist(pid)
        except Exception:
            continue
        if not (title.startswith("2025") or title.startswith("2026")):
            continue
        if not vids:
            continue
        # sort chronologically so rounds read R1 -> final
        vids.sort(key=lambda v: v.get("published",""))
        year = title[:4]
        tournaments.append({
            "tournament": title,
            "year": year,
            "channel": "JomezPro",
            "playlist_id": pid,
            "video_count": len(vids),
            "videos": vids,
        })
        print(f"  {title}: {len(vids)} videos")
    # sort: 2026 before 2025, otherwise by most recent video
    tournaments.sort(key=lambda t: (t["year"], max((v["published"] for v in t["videos"]), default="")), reverse=True)
    out = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "JomezPro playlists",
        "note": "Thumbnails/titles link to YouTube. Grouped by tournament, rounds in order.",
        "tournaments": tournaments,
    }
    Path("data").mkdir(parents=True, exist_ok=True)
    (Path("data") / "videos.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"  saved data/videos.json: {len(tournaments)} tournaments")

if __name__ == "__main__":
    main()
