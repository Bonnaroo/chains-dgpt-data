#!/usr/bin/env python3
"""
Chains - upcoming event field fetcher.
Fetches the registered MPO players for the next upcoming DGPT event from the
PDGA Live API. Saves data/field.json. The app uses this for two things:
  1. The "Who's Registered" display on the Moneyball page (all real entrants).
  2. The draftable player pool for the upcoming event's pick dropdown.
This means whoever is registered IS draftable - no static list needed.
Usage:  python collect_field.py
Output: data/field.json
"""

import json, urllib.request
from datetime import datetime, timezone
from pathlib import Path

# 2026 event IDs in order - script picks the first one without final results
# (i.e. the next upcoming event). Add T11/T12 ids as the season progresses.
EVENT_IDS = [
    ("T1",  96401), ("T2",  96402), ("T3",  96403), ("T4",  97336),
    ("T5",  96404), ("T6",  96407), ("T7",  96408), ("T8",  96409),
    ("T9",  96410), ("T10", 97339), ("T11", 96411), ("T12", 96412),
    ("T13", 96413),
]

HEADERS = {"User-Agent": "Mozilla/5.0"}


def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")


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


def main():
    # find the next upcoming event (first without final results)
    upcoming_tag = upcoming_id = None
    upcoming_players = []
    for tag, eid in EVENT_IDS:
        try:
            players, finished = fetch_field(eid)
            if not finished:
                upcoming_tag, upcoming_id = tag, eid
                upcoming_players = players
                print(f"  upcoming event: {tag} (id {eid}) - {len(players)} registered")
                break
            else:
                print(f"  {tag} (id {eid}): already finished, skipping")
        except Exception as e:
            print(f"  {tag} (id {eid}): error ({e}), skipping")
            continue
    if not upcoming_tag:
        print("  no upcoming event found - season may be complete")
        out = {"updated_at": datetime.now(timezone.utc).isoformat(),
               "event_tag": None, "event_id": None,
               "note": "No upcoming event found.", "players": []}
    else:
        # sort: US players first (most likely to be drafted), then everyone else
        us = [p for p in upcoming_players if p.get("place", 0) == 0]
        out = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "event_tag": upcoming_tag,
            "event_id": upcoming_id,
            "player_count": len(upcoming_players),
            "note": "All registered MPO players. Use as both the 'Who's Registered' "
                    "display and the draftable pool for this event.",
            "players": upcoming_players,
        }
    Path("data").mkdir(parents=True, exist_ok=True)
    (Path("data") / "field.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    print(f"  saved data/field.json: {len(upcoming_players)} players")


if __name__ == "__main__":
    main()
