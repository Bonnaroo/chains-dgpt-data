#!/usr/bin/env python3
"""
Chains - live tournament poller (Railway always-on service).

Polls the PDGA live feed every ~25 seconds and writes scores to Firebase.
- Current round -> /live  (with clean rounds_list + event_final flag).
- Every real round -> /rounds/{eventId}-r{N}  (so the app's round tabs work).
- Every COMPLETED past event is backfilled once into /rounds + /rounds_index
  (so the app can look back at any tournament, round by round).

The current event is chosen AUTOMATICALLY from the season schedule
(data/season.json in chains-dgpt-data) by start_date/end_date.

ROUND NUMBERING NOTE: PDGA does NOT number rounds 1..N. A Major reports
qualifying rounds 1,2,3 and then numbers the Finals "12" and a Playoff "13".
So round numbers are unreliable for "is it over." We publish a clean
rounds_list (real rounds + human labels) and decide an event is FINAL from the
schedule end_date + every player completed - never from a round number.
"""
import json, os, time, urllib.request
from datetime import datetime, timezone

SEASON_URL = os.environ.get(
    "SEASON_URL",
    "https://raw.githubusercontent.com/Bonnaroo/chains-dgpt-data/main/data/season.json",
)
EVENT_ID_FALLBACK = os.environ.get("EVENT_ID", "97339")
FIREBASE_BASE = os.environ.get(
    "FIREBASE_URL",
    "https://chains-fantasy-default-rtdb.firebaseio.com",
).rstrip("/")
POLL_SECONDS = int(os.environ.get("POLL_SECONDS", "25"))
LIVE_API = "https://www.pdga.com/apps/tournament/live-api"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def get(url, timeout=30):
    req = urllib.request.Request(url, headers=HEADERS)
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")

def put_firebase(path, data):
    url = f"{FIREBASE_BASE}/{path}.json"
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="PUT",
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=30).read()

def get_firebase(path):
    """Read a Firebase path; None on miss/err (used for idempotent backfill checks)."""
    try:
        raw = get(f"{FIREBASE_BASE}/{path}.json")
        return json.loads(raw)
    except Exception:
        return None

def _sd(e): return e.get("start_date") or e.get("start")
def _ed(e): return e.get("end_date") or e.get("end")

def load_events():
    sched = json.loads(get(SEASON_URL))
    return [e for e in sched.get("events", []) if _sd(e)]

def current_event():
    """Return the event RECORD live today (or next upcoming) from season.json."""
    try:
        events = load_events()
        today = datetime.now(timezone.utc).date().isoformat()
        live = [e for e in events if _sd(e) <= today <= (_ed(e) or _sd(e))]
        if live:
            return live[0]
        upcoming = sorted((e for e in events if _sd(e) > today), key=_sd)
        if upcoming:
            return upcoming[0]
        if events:
            return sorted(events, key=lambda e: _ed(e) or _sd(e))[-1]
    except Exception as e:
        print(f"[schedule] could not load season.json ({e}); using EVENT_ID fallback")
    return {"event_id": EVENT_ID_FALLBACK}

def round_label(meta, n):
    info = (meta.get("RoundsList", {}) or {}).get(str(n), {}) or {}
    return info.get("Label", f"Round {n}")

def build_rounds_list(meta, event_id, latest):
    """EVERY scheduled round, in order, with labels + archive keys.

    2026-08-26 FIX: this used to skip any round with n > latest ("real rounds
    only"), so round_count was "rounds played so far" and the app read
    "Round 2 of 2" during a 5-round major. PDGA's RoundsList carries the full
    schedule up front - for Worlds that's 1,2,3,4 plus Finals numbered 12 - so
    the whole list is returned and each entry is flagged `played`. The app
    builds its round tabs from this list and already tolerates a tab whose
    archive isn't written yet (loadPastRound catches and marks it "none")."""
    rl = meta.get("RoundsList", {}) or {}
    try:
        nums = sorted(int(k) for k in rl.keys())
    except Exception:
        nums = list(range(1, int(meta.get("Rounds", 3)) + 1))
    if not nums:
        nums = list(range(1, int(meta.get("Rounds", 3)) + 1))
    out = []
    for n in nums:
        info = rl.get(str(n), {}) or {}
        out.append({
            "n": n,
            "label": info.get("Label", f"Round {n}"),
            "abbr": info.get("LabelAbbreviated", str(n)),
            "key": f"{event_id}-r{n}",
            "played": n <= latest,
        })
    if not out:
        out = [{"n": latest, "label": round_label(meta, latest),
                "abbr": str(latest), "key": f"{event_id}-r{latest}"}]
    return out

def fetch_event_meta(event_id):
    ev = json.loads(get(f"{LIVE_API}/live_results_fetch_event?TournID={event_id}&Division=MPO"))
    return ev.get("data", {})

def fetch_round(event_id, round_num, meta):
    rd = json.loads(get(f"{LIVE_API}/live_results_fetch_round?TournID={event_id}&Division=MPO&Round={round_num}"))
    rdata = rd.get("data", {})
    # 2026-08-26 FIX: `data` is a dict for a single-pool event but a LIST of pool
    # objects when the field is split across courses (Worlds 2026: pool A on
    # Black Locust, pool B on Toboggan). Assuming a dict crashed every cycle of
    # a multi-pool major, so /live froze on the last single-pool event.
    pools = rdata if isinstance(rdata, list) else [rdata]
    scores, pool_meta = [], []
    for pl in pools:
        if not isinstance(pl, dict):
            continue
        pname = pl.get("pool")
        course = None
        for L in (pl.get("layouts") or []):
            if isinstance(L, dict) and L.get("Name"):
                course = L.get("Name"); break
        pholes = [{"hole": h.get("Hole"), "par": h.get("Par"), "length": h.get("Length")}
                  for h in (pl.get("holes") or [])]
        pool_meta.append({"pool": pname, "course": course, "holes": pholes})
        for s in (pl.get("scores") or []):
            s["_pool"] = pname
            scores.append(s)
    # `holes` keeps the first pool's layout for backward compatibility.
    holes = pool_meta[0]["holes"] if pool_meta else []
    players = []
    for p in scores:
        hs = p.get("HoleScores", [])
        pts = p.get("PlayerThrowStatus") or {}
        players.append({
            "name": p.get("Name"), "short": p.get("ShortName"),
            "pdga": p.get("PDGANum"), "place": p.get("RunningPlace"),
            "tied": p.get("Tied", False),
            "event_to_par": p.get("ToPar"), "round_to_par": p.get("RoundtoPar"),
            "thru": len([h for h in hs if h]), "hole_scores": hs,
            "status": p.get("RoundStatus"), "completed": p.get("Completed"),
            "card": p.get("CardNum"), "tee_time": p.get("TeeTime"),
            "cur_hole": pts.get("HoleOrdinal"), "cur_throw": pts.get("ThrowCount"),
            "cur_dist": pts.get("DistanceToTarget"), "cur_zone": pts.get("ZoneID"),
            "pool": p.get("_pool"),
        })
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "event_id": event_id,
        "event_name": meta.get("Name", ""),
        "round": round_num,
        "round_label": round_label(meta, round_num),
        "latest_round": meta.get("LatestRound", 1),
        "highest_completed_round": meta.get("HighestCompletedRound", 0),
        "rounds": meta.get("Rounds", 3),
        "holes": holes, "pools": pool_meta,
        "player_count": len(players), "players": players,
    }

def is_final(end_date, today, latest, highest_completed, players):
    """Truly-final signal: end_date reached AND no one still on the course AND the
    latest round is fully complete. Never trusts a round number alone."""
    if not end_date or today < end_date:
        return False
    if not players:
        return False
    if any(p.get("status") == "I" for p in players):
        return False
    return highest_completed >= latest

def backfill_next_completed_event(today):
    """Archive ONE not-yet-indexed completed event per call, so each poll cycle stays
    light (never a long blocking sweep). Per-round resumable + resilient: skips rounds
    already saved and skips a round that errors. Returns True if it touched an event."""
    try:
        events = load_events()
    except Exception as e:
        print(f"[backfill] could not load schedule: {e}")
        return False
    for rec in events:
        end = _ed(rec)
        if not end or end >= today:        # only fully-finished events
            continue
        eid = str(rec["event_id"])
        if get_firebase(f"rounds_index/{eid}"):   # already done
            continue
        try:
            meta = fetch_event_meta(eid)
            latest = meta.get("LatestRound", 1)
            rl = build_rounds_list(meta, eid, latest)
            for r in rl:
                rkey = f"{eid}-r{r['n']}"
                if get_firebase(f"rounds/{rkey}") is not None:
                    continue               # resume: already archived
                try:
                    put_firebase(f"rounds/{rkey}", fetch_round(eid, r["n"], meta))
                except Exception as e:
                    print(f"[backfill] {rkey} skipped: {e}")
            put_firebase(f"rounds_index/{eid}", {
                "event_id": eid, "event_name": meta.get("Name", ""),
                "rounds_list": rl, "rounds": meta.get("Rounds", 3),
                "event_final": True,
                "finalized_at": datetime.now(timezone.utc).isoformat(),
            })
            print(f"[backfill] archived event {eid} ({len(rl)} rounds)")
        except Exception as e:
            print(f"[backfill] event {eid} failed: {e}")
        return True                        # one event per call -> light cycles

def run_once():
    """One poll cycle: read the schedule, fetch the live round, push to
    Firebase /live (+ archive the current round). Safe to call from cron/CI.
    Returns a short status string. Raises on hard failure."""
    today = datetime.now(timezone.utc).date().isoformat()
    rec = current_event()
    event_id = str(rec["event_id"])
    meta = fetch_event_meta(event_id)
    latest = meta.get("LatestRound", 1)
    rounds_list = build_rounds_list(meta, event_id, latest)

    live = fetch_round(event_id, latest, meta)
    live["rounds_list"] = rounds_list
    live["current_round"] = latest
    live["current_round_label"] = round_label(meta, latest)
    live["round_count"] = len(rounds_list)
    live["round_index"] = next((i + 1 for i, r in enumerate(rounds_list)
                                if r["n"] == latest), len(rounds_list))
    live["event_final"] = is_final(_ed(rec), today, latest,
                                   live["highest_completed_round"], live["players"])
    put_firebase("live", live)
    try:
        put_firebase(f"rounds/{event_id}-r{latest}", live)
    except Exception as e:
        print(f"[archive] {e}")

    active = len([p for p in live["players"] if p["status"] == "I"])
    return (f"event {event_id} {live['current_round_label']} "
            f"({live['round_index']}/{live['round_count']}) "
            f"{live['player_count']} players, {active} on course"
            + (" [FINAL]" if live["event_final"] else ""))


if __name__ == "__main__":
    print(run_once())
