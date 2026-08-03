#!/usr/bin/env python3
"""
Chains - upcoming event field fetcher.
Fetches the registered MPO players for the next upcoming DGPT event from the
PDGA Live API. Saves data/field.json. The app uses this for two things:
  1. The "Who's Registered" display (all real entrants).
  2. The draftable player pool for the upcoming event's pick dropdown.
This means whoever is registered IS draftable - no static list needed.

2026-08-03 FIX: the event list used to be hardcoded here and stopped at T14, so
the moment Ledgestone finished this script walked the whole season, found every
event complete, and wrote "No upcoming event found" - leaving the app with an
empty field while picks were open for Discmania. The list now comes from
data/season.json (the schedule everything else already uses), so it can never
fall behind the season again. The hardcoded list stays only as a fallback if
season.json can't be read.

Also records field stability, so the app can answer "is registration done?":
  player_count       - how many are registered right now
  count_changed_at   - the last time that number actually changed
  stable_hours       - how long it has been unchanged
A field that hasn't moved in ~24h is settled. Note the count can hold steady
while names churn (withdrawals backfilled from the waitlist), so we also track
a roster fingerprint.

Usage:  python collect_field.py
Output: data/field.json
"""

import json, hashlib, urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Fallback only - used if data/season.json is unreadable. Prefer season.json.
FALLBACK_EVENT_IDS = [
    ("T1",  96401), ("T2",  96402), ("T3",  96403), ("T4",  97336),
    ("T5",  96404), ("T6",  96407), ("T7",  96408), ("T8",  96409),
    ("T9",  96410), ("T10", 97339), ("T11", 96411), ("T12", 96412),
    ("T13", 96413), ("T14", 96414), ("T15", 96415),
]

HEADERS = {"User-Agent": "Mozilla/5.0"}
FIELD_PATH = Path("data") / "field.json"


def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")


def event_ids():
    """Season schedule is the source of truth; hardcoded list is the fallback."""
    try:
        season = json.loads((Path("data") / "season.json").read_text(encoding="utf-8"))
        events = season.get("events") if isinstance(season, dict) else season
        out = []
        for e in events or []:
            t, eid = e.get("t"), e.get("event_id")
            if t is None or not eid:
                continue
            out.append((f"T{t}", int(eid)))
        out.sort(key=lambda x: int(x[0][1:]))
        if out:
            print(f"  schedule: {len(out)} events from season.json (T1-{out[-1][0]})")
            return out
        print("  season.json had no usable events - using fallback list")
    except Exception as e:
        print(f"  couldn't read season.json ({e}) - using fallback list")
    return FALLBACK_EVENT_IDS


def fetch_field(event_id):
    url = f"https://www.pdga.com/api/v1/feat/live-tournaments/{event_id}/event-division-results/MPO"
    d = json.loads(get(url))
    results = d.get("results", [])
    players = []
    has_final_results = False
    for x in results:
        l = x.get("liveResult", {})
        fn = l.get("firstName", "").strip()
        ln = l.get("lastName", "").strip()
        pdga = l.get("pdgaNum") or l.get("pdgaNumber")
        place = l.get("place", 0)
        to_par = l.get("toPar")
        # skip placeholders
        if not ln or any(w in (fn + " " + ln) for w in
                         ("Exemption", "Qualifier", "Monday", "DGPT", "Event")):
            continue
        if place and place > 0 and to_par is not None:
            has_final_results = True
        players.append({
            "firstName": fn,
            "lastName": ln,
            "pdgaNumber": pdga,
            "place": place,
        })
    return players, has_final_results


def roster_hash(players):
    ids = sorted(str(p.get("pdgaNumber") or (p.get("firstName", "") + p.get("lastName", "")))
                 for p in players)
    return hashlib.sha1("|".join(ids).encode("utf-8")).hexdigest()[:12]


def previous():
    try:
        return json.loads(FIELD_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main():
    now = datetime.now(timezone.utc)
    upcoming_tag = upcoming_id = None
    upcoming_players = []

    for tag, eid in event_ids():
        try:
            players, finished = fetch_field(eid)
            if not finished:
                upcoming_tag, upcoming_id = tag, eid
                upcoming_players = players
                print(f"  upcoming event: {tag} (id {eid}) - {len(players)} registered")
                break
            print(f"  {tag} (id {eid}): already finished, skipping")
        except Exception as e:
            print(f"  {tag} (id {eid}): error ({e}), skipping")
            continue

    if not upcoming_tag:
        print("  no upcoming event found - season may be complete")
        out = {"updated_at": now.isoformat(), "event_tag": None, "event_id": None,
               "note": "No upcoming event found.", "players": []}
    else:
        prev = previous()
        rhash = roster_hash(upcoming_players)
        same_event = prev.get("event_id") == upcoming_id
        changed = (not same_event
                   or prev.get("player_count") != len(upcoming_players)
                   or prev.get("roster_hash") != rhash)

        changed_at = now.isoformat() if changed else (
            prev.get("count_changed_at") or now.isoformat())
        try:
            delta = now - datetime.fromisoformat(changed_at)
            stable_hours = round(delta.total_seconds() / 3600, 1)
        except Exception:
            stable_hours = 0.0

        print(f"  roster {'CHANGED' if changed else 'unchanged'} "
              f"({len(upcoming_players)} players, stable {stable_hours}h)")

        out = {
            "updated_at": now.isoformat(),
            "event_tag": upcoming_tag,
            "event_id": upcoming_id,
            "player_count": len(upcoming_players),
            "roster_hash": rhash,
            "count_changed_at": changed_at,
            "stable_hours": stable_hours,
            "note": "All registered MPO players. Use as both the 'Who's Registered' "
                    "display and the draftable pool for this event. "
                    "stable_hours = how long the roster has been unchanged; "
                    "over ~24h means registration has effectively settled, though "
                    "withdrawals can still swap names right up to tee-off.",
            "players": upcoming_players,
        }

    FIELD_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIELD_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"  saved data/field.json: {len(upcoming_players)} players")


if __name__ == "__main__":
    main()
