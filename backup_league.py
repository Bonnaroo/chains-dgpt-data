#!/usr/bin/env python3
"""
Chains - league data backup.
Snapshots the entire Firebase league node and saves a timestamped copy
into data/backups/ in the repo. These are PERMANENT (never rotate away),
giving a full history on top of the app's 10 rotating Firebase backups.

Run daily (and can be run manually anytime). Keeps the league data safe
forever — if anything ever corrupts the live data, you can restore from
any dated snapshot here.

Usage:  python backup_league.py
Output: data/backups/league-YYYY-MM-DD.json  (+ updates latest.json)
"""
import json, urllib.request
from datetime import datetime, timezone
from pathlib import Path

FIREBASE = "https://chains-fantasy-default-rtdb.firebaseio.com/league.json"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def get(url, timeout=30):
    req = urllib.request.Request(url, headers=HEADERS)
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")

def main():
    backup_dir = Path("data/backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    try:
        raw = get(FIREBASE)
        data = json.loads(raw)
    except Exception as e:
        print(f"  backup FAILED: {e}")
        return
    if not data:
        print("  WARNING: league node is empty — NOT overwriting backups")
        return
    # sanity check: must contain picks before we trust it
    keys = data.get("keys", {})
    has_picks = any("picks" in k for k in keys.keys()) if isinstance(keys, dict) else False
    if not has_picks:
        print("  WARNING: snapshot has no picks — skipping to avoid saving bad data")
        return
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    snapshot = {
        "backed_up_at": datetime.now(timezone.utc).isoformat(),
        "source": "firebase /league",
        "data": data,
    }
    # dated permanent snapshot (one per day; re-running same day overwrites that day)
    dated = backup_dir / f"league-{today}.json"
    dated.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    # always-current pointer
    latest = backup_dir / "latest.json"
    latest.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    # count picks events for the log
    pick_events = [k for k in keys.keys() if "picks" in k]
    print(f"  backup OK: {dated.name} | {len(keys)} keys, {len(pick_events)} pick events")

if __name__ == "__main__":
    main()
