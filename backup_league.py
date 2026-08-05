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

2026-08-05 (Auditor, TRIAGE_AND_AUDIT.md queue item 8 fast-follow): added the
same drop-detection check already shipped in backup_rounds.py
(commit 533453d0c0dcbe72ba13f936680ce7b2d2c7000c) against the previous
backup (latest.json) before overwriting it. This script previously only
warned on a totally-empty read or a snapshot with zero picks-containing
keys, so a *partial* data loss (e.g. half the pick-event keys silently
vanishing) would still pass both existing checks and rotate in silently --
exactly the "recurring Firebase rollback" failure mode already tracked in
company/LESSONS_LEARNED.md (Issues #28/#39) and already proven to happen for
real in the rounds data (see backup_rounds.py's docstring / AUDIT_LOG.md Run
7). We still save the new snapshot either way (skipping could itself destroy
the only durable copy of a legitimate deletion), but a big drop in the
`keys` count now prints a loud, greppable WARNING line so the daily Action
log / any log monitor surfaces it instead of the file quietly rotating over
real data loss. This script is read-only against chains-fantasy /league --
no write is ever made to that path.
"""
import json, urllib.request
from datetime import datetime, timezone
from pathlib import Path

FIREBASE = "https://chains-fantasy-default-rtdb.firebaseio.com/league.json"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# If the new snapshot has fewer than this fraction of the previous snapshot's
# `keys` count, treat it as a possible data-loss event and warn loudly
# (but still save -- see note above).
DROP_WARN_THRESHOLD = 0.5

def get(url, timeout=30):
    req = urllib.request.Request(url, headers=HEADERS)
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")

def previous_keys_count(backup_dir):
    """Best-effort read of the prior snapshot's `keys` count, for
    drop detection. Returns None if there's no prior snapshot to compare
    against (first-ever run, or file missing/unreadable)."""
    latest = backup_dir / "latest.json"
    if not latest.exists():
        return None
    try:
        prev = json.loads(latest.read_text(encoding="utf-8"))
        prev_keys = (prev.get("data") or {}).get("keys") or {}
        return len(prev_keys) if isinstance(prev_keys, dict) else None
    except Exception:
        return None

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

    total_keys = len(keys) if isinstance(keys, dict) else 0
    prev_total = previous_keys_count(backup_dir)
    if prev_total is not None and prev_total > 0 and total_keys < prev_total * DROP_WARN_THRESHOLD:
        print(
            f"  *** WARNING: POSSIBLE DATA LOSS *** /league keys dropped from "
            f"{prev_total} to {total_keys} (more than {int((1 - DROP_WARN_THRESHOLD) * 100)}% "
            f"decrease) since the last backup. Saving this snapshot anyway (per "
            f"chains-firebase-backup skill), but this matches the known Firebase "
            f"rollback pattern in company/LESSONS_LEARNED.md (Issues #28/#39) and "
            f"should be investigated, not silently rotated over."
        )

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
    print(f"  backup OK: {dated.name} | {total_keys} keys, {len(pick_events)} pick events")

if __name__ == "__main__":
    main()
