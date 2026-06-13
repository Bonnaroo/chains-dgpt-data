#!/usr/bin/env python3

"""
Chains Fantasy Disc Golf -- PDGA event collector.

One job: fetch one event's results + stats from the PDGA Live API and
save a single clean JSON file. No HTML scraping, no StatMando, no API key.

Usage:
    python collect_event.py 96401
    python collect_event.py 96401 --division FPO

Output:
    data/events/<event_id>-<division>.json
"""

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Stat ID -> human label. Source: PDGA Live stats endpoint.
# We store ALL stats every time, even ones we don't score on yet, so the
# season history can be re-scored later under any rules.
# ---------------------------------------------------------------------------

STAT_LABELS = {
    1:  "fairway_hits_pct",
    2:  "c1_in_reg_pct",
    3:  "c2_in_reg_pct",
    4:  "parked_pct",
    5:  "scramble_pct",
    6:  "c1_putting_pct",
    7:  "c1x_putting_pct",
    8:  "c2_putting_pct",
    9:  "ob_rate_pct",
    10: "birdie_rate_pct",
    11: "double_bogey_or_worse_count",
    12: "bogey_count",
    13: "par_count",
    14: "birdie_count",
    15: "eagle_or_better_count",
    16: "putting_total_distance_ft",
    17: "longest_throw_in",
    18: "putting_average_distance",
    21: "ob_count",
    22: "bogey_rate_pct",
    100: "strokes_gained_total",
    101: "strokes_gained_putting",
    102: "strokes_gained_tee_to_green",
    103: "strokes_lost_ob",
    104: "strokes_gained_c1x",
    105: "strokes_gained_c2",
}

BASE = "https://www.pdga.com/api/v1/feat"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

def fetch_json(url):
    """GET a URL and return parsed JSON. Raises on non-200."""
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def collect(event_id, division="MPO"):
    results_url = f"{BASE}/live-tournaments/{event_id}/event-division-results/{division}"
    stats_url = f"{BASE}/stats/tournament-division-stats/{event_id}/{division}"

    print(f"  fetching results: {results_url}")
    results_raw = fetch_json(results_url)

    print(f"  fetching stats:   {stats_url}")
    try:
        stats_raw = fetch_json(stats_url)
    except Exception as e:
        print(f"  (stats unavailable: {e})")
        stats_raw = {"resultStats": []}

    tournament = results_raw.get("tournament", {})
    live_rounds = results_raw.get("liveRounds", [])

    # Build a stats lookup keyed by resultId. The stats endpoint does NOT
    # carry PDGA number, but both endpoints share resultId, so we join on that.
    stats_by_result_id = {}
    for entry in stats_raw.get("resultStats", []):
        res = entry.get("result", {})
        rid = res.get("resultId")
        if rid is None:
            continue
        clean_stats = {}
        for s in entry.get("stats", []):
            label = STAT_LABELS.get(s["statId"], f"stat_{s['statId']}")
            clean_stats[label] = {
                "value": s.get("statValue"),
                "count": s.get("statCount"),
                "opportunities": s.get("statOpportunityCount"),
                "rank": s.get("rank"),
            }
        stats_by_result_id[rid] = clean_stats

    # Build player list, joining results + stats.
    players = []
    for p in results_raw.get("results", []):
        r = p.get("liveResult", {})
        pdga = r.get("pdgaNum")
        result_id = r.get("resultId")
        rounds = [
            {
                "round_id": rr.get("roundId"),
                "score": rr.get("score"),
                "rating": rr.get("ratingOfficial"),
                "place_after": rr.get("overallPlace"),
            }
            for rr in r.get("liveRoundResults", [])
        ]
        players.append({
            "pdga_number": pdga,
            "first_name": r.get("firstName"),
            "last_name": r.get("lastName"),
            "place": r.get("place"),
            "tied": r.get("tied"),
            "total_strokes": r.get("total"),
            "to_par": r.get("toPar"),
            "prize_usd": r.get("prize"),
            "points": r.get("points"),
            "dnf": r.get("dnf"),
            "event_rating": p.get("eventRating"),
            "rounds": rounds,
            "stats": stats_by_result_id.get(result_id, {}),
        })

    return {
        "event_id": event_id,
        "division": division,
        "event_name": tournament.get("tournamentName"),
        "rounds_count": tournament.get("rounds"),
        "round_ids": [lr.get("roundId") for lr in live_rounds],
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "source": results_url,
        "players": players,
    }

def main():
    ap = argparse.ArgumentParser(description="Collect one PDGA event into a JSON file.")
    ap.add_argument("event_id", help="PDGA event ID, e.g. 96401")
    ap.add_argument("--division", default="MPO", help="Division (default MPO)")
    ap.add_argument("--out", default="data/events", help="Output folder")
    args = ap.parse_args()

    print(f"Collecting event {args.event_id} ({args.division})...")
    data = collect(args.event_id, args.division)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.event_id}-{args.division}.json"
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    n = len(data["players"])
    with_stats = sum(1 for p in data["players"] if p["stats"])
    print(f"  saved {out_path}")
    print(f"  {n} players, {with_stats} with stats, {data['rounds_count']} rounds")

    if data["players"]:
        top = data["players"][0]
        print(f"  winner: {top['first_name']} {top['last_name']} "
              f"({top['to_par']}, ${top['prize_usd']})")

if __name__ == "__main__":
    main()
