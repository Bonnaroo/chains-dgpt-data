#!/usr/bin/env python3
"""
Chains - video fetcher (YouTube Data API, MPO only, by tournament).
Uses the YouTube Data API v3 to get the FULL video list of each Jomez Pro
tournament playlist (the RSS feed caps at 15 and was dropping final rounds on
big events). MPO only. Grouped by tournament, rounds in chronological order.
Requires env var YOUTUBE_API_KEY (stored as a GitHub Actions secret).
If the key is missing, it falls back to the RSS method (15-video cap) so the
pipeline never hard-fails.
Usage:  python collect_videos.py
Output: data/videos.json
"""

import json, os, re, urllib.request, urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

JOMEZ_CHANNEL_ID = "UCmGyCEbHfY91NFwHgioNLMQ"
JOMEZ_PLAYLISTS_URL = "https://www.youtube.com/@JomezPro/playlists"
API_KEY = os.environ.get("YOUTUBE_API_KEY", "").strip()
HEADERS = {"User-Agent": "Mozilla/5.0"}
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}

import re as _re
ROUNDRE = re.compile(r'\b(R[1-9][FB]9|FINAL\s*[FB]9|FINALF9|FINALB9)\b', re.I)

def classify_kind(title):
    """Tournament round vs practice/extra, based on the R#F9/FINAL pattern."""
    return "round" if ROUNDRE.search(title or "") else "practice"

def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")

def discover_playlists():
    """Find Jomez playlist IDs from their playlists page."""
    html = get(JOMEZ_PLAYLISTS_URL)
    return list(dict.fromkeys(re.findall(r'"playlistId":"(PL[^"]+)"', html)))

def playlist_title_via_rss(pid):
    try:
        x = get(f"https://www.youtube.com/feeds/videos.xml?playlist_id={pid}")
        root = ET.fromstring(x)
        return root.findtext("a:title", default="", namespaces=NS).strip()
    except Exception:
        return ""

def playlist_videos_api(pid):
    """Full playlist via API with pagination. Returns list of (title, video_id, published)."""
    items, page = [], ""
    while True:
        params = urllib.parse.urlencode({
            "part": "snippet", "playlistId": pid, "maxResults": 50,
            "pageToken": page, "key": API_KEY,
        })
        data = json.loads(get(f"https://www.googleapis.com/youtube/v3/playlistItems?{params}"))
        for it in data.get("items", []):
            sn = it.get("snippet", {})
            vid = sn.get("resourceId", {}).get("videoId")
            title = sn.get("title", "")
            pub = sn.get("publishedAt", "")
            if vid and title:
                # skip private/unavailable videos
                if title.lower() in ('private video', 'deleted video'):
                    continue
                thumbs = sn.get('thumbnails', {})
                if not thumbs:
                    continue
                items.append((title, vid, pub))
        page = data.get("nextPageToken", "")
        if not page:
            break
    return items

def playlist_videos_rss(pid):
    """Fallback: RSS (capped at 15)."""
    x = get(f"https://www.youtube.com/feeds/videos.xml?playlist_id={pid}")
    root = ET.fromstring(x)
    out = []
    for e in root.findall("a:entry", NS):
        vid = e.findtext("yt:videoId", default="", namespaces=NS)
        title = e.findtext("a:title", default="", namespaces=NS).strip()
        pub = e.findtext("a:published", default="", namespaces=NS)
        if vid and title:
            out.append((title, vid, pub))
    return out

def main():
    use_api = bool(API_KEY)
    print(f"  mode: {'API (full playlists)' if use_api else 'RSS fallback (15-cap)'}")
    pids = discover_playlists()
    tournaments = []
    for pid in pids[:40]:
        title = playlist_title_via_rss(pid)
        if not (title.startswith("2025") or title.startswith("2026")):
            continue
        if any(w in title.lower() for w in ("women", "throw pink")):
            continue
        try:
            raw = playlist_videos_api(pid) if use_api else playlist_videos_rss(pid)
        except Exception as e:
            print(f"    {title}: fetch error ({e}); skipping")
            continue
        # MPO only, drop FPO
        vids = []
        for t, v, pub in raw:
            if "fpo" in t.lower():
                continue
            vids.append({
                "title": t.strip(), "video_id": v,
                "kind": classify_kind(t),
                "link": f"https://www.youtube.com/watch?v={v}",
                "thumbnail": f"https://i.ytimg.com/vi/{v}/hqdefault.jpg",
                "published": pub,
            })
        if not vids:
            continue
        vids.sort(key=lambda x: x.get("published", ""))  # R1 -> final
        rounds_n = sum(1 for v in vids if v["kind"] == "round")
        practice_n = sum(1 for v in vids if v["kind"] == "practice")
        tournaments.append({
            "tournament": title, "year": title[:4], "channel": "JomezPro",
            "playlist_id": pid, "video_count": len(vids),
            "round_count": rounds_n, "practice_count": practice_n,
            "videos": vids,
        })
        print(f"    {title}: {len(vids)} MPO videos")
    tournaments.sort(key=lambda t: (t["year"], max((v["published"] for v in t["videos"]), default="")), reverse=True)
    out = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "JomezPro playlists (YouTube Data API)" if use_api else "JomezPro playlists (RSS, 15-cap)",
        "note": "MPO only. Grouped by tournament, rounds in order. Links open YouTube.",
        "tournaments": tournaments,
    }
    Path("data").mkdir(parents=True, exist_ok=True)
    (Path("data") / "videos.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"  saved data/videos.json: {len(tournaments)} tournaments")

if __name__ == "__main__":
    main()
