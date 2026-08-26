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
from datetime import datetime, timezone, timedelta
from pathlib import Path

HEADERS = {"User-Agent": "Mozilla/5.0"}

# 2026-08-26 FIX: the active event used to be the hardcoded constant below,
# only overridable by hand via live_event.txt. Nobody updates it mid-season, so
# from the European Open (June) until Worlds this script re-fetched a FINISHED
# June tournament every 5 minutes and the app's Live screen never showed the
# event actually being played. The event is now derived from data/season.json
# (the same schedule collect_field.py uses) by date window, so it follows the
# season automatically. live_event.txt still wins if present, as a manual
# override for odd cases; the constant is only a last-ditch fallback.
DEFAULT_EVENT = "97339"  # legacy fallback only - T10 European Open

# How many days of slack around a scheduled event still counts as "live"
# (covers timezone skew and weather delays pushing a final round).
WINDOW_DAYS = 1


def active_event_from_season():
    """Return the event_id whose scheduled date window contains today (UTC),
    or None if the season is between events."""
    try:
        season = json.loads((Path("data") / "season.json").read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  couldn't read season.json ({e})")
        return None
    events = season.get("events") if isinstance(season, dict) else season
    today = datetime.now(timezone.utc).date()
    for e in events or []:
        eid, sd, ed = e.get("event_id"), e.get("start_date"), e.get("end_date")
        if not (eid and sd and ed):
            continue
        try:
            start = datetime.strptime(sd, "%Y-%m-%d").date()
            end = datetime.strptime(ed, "%Y-%m-%d").date()
        except Exception:
            continue
        if (start - timedelta(days=WINDOW_DAYS)) <= today <= (end + timedelta(days=WINDOW_DAYS)):
            print(f"  active event from season.json: T{e.get('t')} {e.get('name')} ({eid})")
            return str(eid)
    print("  no event in its date window today - season is between events")
    return None


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
    # NOTE: `data` is a dict for a single-pool event, but a LIST of pool objects
    # when the field is split across courses (Worlds 2026: pool A on Black
    # Locust, pool B on Toboggan, 104 players each). Assuming a dict here made
    # the collector throw on every run of a multi-pool major.
    rd = json.loads(get(f"{base}/live_results_fetch_round?TournID={event_id}&Division=MPO&Round={latest}"))
    rdata = rd.get("data", {})
    pools = rdata if isinstance(rdata, list) else [rdata]

    scores = []
    pool_meta = []
    for pl in pools:
        if not isinstance(pl, dict):
            continue
        pname = pl.get("pool")
        layouts = pl.get("layouts") or []
        course = None
        for L in layouts:
            if isinstance(L, dict) and L.get("Name"):
                course = L.get("Name"); break
        phraw = pl.get("holes") or []
        pholes = [{"hole": h.get("Hole"), "par": h.get("Par"), "length": h.get("Length")}
                  for h in phraw]
        pool_meta.append({"pool": pname, "course": course, "holes": pholes})
        for s in (pl.get("scores") or []):
            s["_pool"] = pname
            scores.append(s)

    # `holes` stays the first pool's layout for backward compatibility; per-pool
    # layouts live in `pools` since a split field has different pars per course.
    holes = pool_meta[0]["holes"] if pool_meta else []
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
            "pool": p.get("_pool"),
        })
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "event_id": event_id,
        "event_name": name,
        "latest_round": latest,
        "highest_completed_round": highest,
        "rounds": rounds,
        "holes": holes,
        "pools": pool_meta,
        "player_count": len(players),
        "players": players,
    }


def main():
    # 1. manual override wins, 2. otherwise derive from the season schedule,
    # 3. only then the legacy constant.
    event_id = None
    p = Path("live_event.txt")
    if p.exists():
        txt = p.read_text().strip()
        if txt and txt.isdigit():
            event_id = txt
            print(f"  using live_event.txt override: {event_id}")
    if not event_id:
        event_id = active_event_from_season()

    Path("data").mkdir(parents=True, exist_ok=True)

    if not event_id:
        # Nothing is being played today. Write an explicit idle file rather than
        # leaving the last event's scores sitting there looking live.
        out = {"updated_at": datetime.now(timezone.utc).isoformat(),
               "event_id": None, "event_name": None, "live": False,
               "note": "No event in its date window today.", "players": []}
        (Path("data") / "live.json").write_text(json.dumps(out), encoding="utf-8")
        print("  live.json: idle (no event today)")
        return

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


def push_firebase_live():
    """Also push the poller-shaped payload to Firebase /live, which is what the
    app's Live Chains screen actually reads. This used to be done only by
    poller.py running as an always-on loop on a personal machine; when that
    machine stopped, /live froze on a finished event and Live Chains showed
    "between tournaments" during a live major. Running it here means the
    existing every-5-minutes workflow keeps /live fresh with no babysitting.
    Guarded so a failure here can never break the data/live.json write above."""
    try:
        import poller_once
        print("  firebase /live: " + poller_once.run_once())
    except Exception as e:
        print(f"  firebase /live push failed: {e}")


if __name__ == "__main__":
    main()
    push_firebase_live()
