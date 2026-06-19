#!/usr/bin/env python3
"""
Chains - live tournament scores fetcher.
Fetches the live PDGA feed for the currently-active event and writes a
compact file (data/live.json) the app reads directly (no CORS, no proxies).
Pulls: full field, every hole score, each player's current hole + throw
status, live placement. Runs frequently during tournament days.
Usage:  python collect_live.py
Output: data/live.json  (or live.json with empty flag if no live event)
"""
import json, urllib.request, urllib.parse
from datetime import datetime, timezone
from pathlib import Path

HEADERS = {"User-Agent": "Mozilla/5.0"}

# The currently active event. Update this ID per event, OR derive from
# events.txt + checking which is live. For now, read from live_event.txt
# if present, else fall back to the constant.
DEFAULT_EVENT = "97339"  # T10 European Open


def get(url, timeout=30):
    req = urllib.request.Request(url, headers=HEADERS)
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")


def fetch_live(event_id):
    base = "https://www.pdga.com/apps/tournament/live-api"
    # 1. event meta -> current round
    ev = json.loads(get(f"{base}/live_results_fetch_event?TournID={event_id}&Division=MPO"))
    data = ev.get("data", {})
    latest = data.get("LatestRound", 1)
    highest = data.get("HighestCompletedRound", 0)
    rounds = data.get("Rounds", 3)
    name = data.get("Name", "")
    # 2. fetch the current round's full field
    rd = json.loads(get(f"{base}/live_results_fetch_round?TournID={event_id}&Division=MPO&Round={latest}"))
    rdata = rd.get("data", {})
    scores = rdata.get("scores", [])
    holes_raw = rdata.get("holes", [])
    # compact hole info
    holes = [{"hole": h.get("Hole"), "par": h.get("Par"), "length": h.get("Length")}
             for h in holes_raw]
    # compact per-player records
    players = []
    for p in scores:
        hole_scores = p.get("HoleScores", [])
        thru = len([h for h in hole_scores if h])
        pts = p.get("PlayerThrowStatus") or {}
        players.append({
            "name": p.get("Name"),
            "short": p.get("ShortName"),
            "pdga": p.get("PDGANum"),
            "place": p.get("RunningPlace"),
            "tied": p.get("Tied", False),
            "event_to_par": p.get("ToPar"),
            "round_to_par": p.get("RoundtoPar"),
            "thru": thru,
            "hole_scores": hole_scores,
            "status": p.get("RoundStatus"),      # "I" = in progress
            "completed": p.get("Completed"),
            "card": p.get("CardNum"),
            "tee_time": p.get("TeeTime"),
            # current-hole throw tracker (when mid-hole)
            "cur_hole": pts.get("HoleOrdinal"),
            "cur_throw": pts.get("ThrowCount"),
            "cur_dist": pts.get("DistanceToTarget"),
            "cur_zone": pts.get("ZoneID"),
        })
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "event_id": event_id,
        "event_name": name,
        "latest_round": latest,
        "highest_completed_round": highest,
        "rounds": rounds,
        "holes": holes,
        "player_count": len(players),
        "players": players,
    }


def main():
    # allow override via live_event.txt (single line with event id)
    event_id = DEFAULT_EVENT
    p = Path("live_event.txt")
    if p.exists():
        txt = p.read_text().strip()
        if txt and txt.isdigit():
            event_id = txt
    Path("data").mkdir(parents=True, exist_ok=True)
    try:
        out = fetch_live(event_id)
        (Path("data") / "live.json").write_text(json.dumps(out), encoding="utf-8")
        active = len([p for p in out["players"] if p["status"] == "I"])
        print(f"  live.json: event {event_id}, R{out['latest_round']}, "
              f"{out['player_count']} players, {active} on course")
    except Exception as e:
        # write an empty-but-valid file so the app shows a clean state
        out = {"updated_at": datetime.now(timezone.utc).isoformat(),
               "event_id": event_id, "error": str(e), "players": []}
        (Path("data") / "live.json").write_text(json.dumps(out), encoding="utf-8")
        print(f"  live.json: no live data ({e})")


if __name__ == "__main__":
    main()
