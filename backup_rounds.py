#!/usr/bin/env python3
"""
Chains - Go Throw rounds backup.
Snapshots every saved round from the CHAINS APP Firebase project
(chains-app-f38f8 - separate project from the fantasy-league chains-fantasy
DB that backup_league.py covers) into data/backups/ in this repo.

Round DATA lives at the TOP-LEVEL nodes:
  /playRounds/{roundId}  - the durable store of rounds (open + finished),
                           each a full object: course, date, owner, players
                           (with holeScores/thru/total), status, weather, ...
  /liveRounds/{roundId}  - in-progress rounds currently being watched live
                           (mirror of the open playRounds).

(An older path users/{uid}/rounds only ever held a stale boolean index for a
legacy test user and NO real round data - do not rely on it.)

Reads require an authenticated request; anonymous auth is enough (the app
signs users in anonymously by default), so this script signs in anonymously
via the Firebase Identity Toolkit REST API using the app's public web API key
(not a secret; it ships in the client bundle) before reading.

Run daily (and can be run manually anytime).
Output: data/backups/rounds-YYYY-MM-DD.json  (+ updates rounds-latest.json)

2026-08-05 (Auditor, TRIAGE_AND_AUDIT.md queue item 8): added a drop-detection
check against the previous backup (rounds-latest.json) before overwriting it.
This script previously only warned on a *totally empty* /playRounds read, so a
partial data loss (observed for real: 5 playRounds on 2026-07-28 down to 1 on
2026-07-29, an 80% drop, committed with zero warning -- see
data/backups/rounds-2026-07-28.json vs rounds-2026-07-29.json in this repo)
was saved and rotated in silently, exactly the "recurring Firebase
rollback" failure mode already tracked in company/LESSONS_LEARNED.md
(Issues #28/#39). We still save the new snapshot either way (skipping could
itself destroy the only durable copy of a legitimate deletion), but a big drop
now prints a loud, greppable WARNING line so the daily Action log / any log
monitor surfaces it instead of the file quietly rotating over real data loss.
"""
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_KEY = "AIzaSyAZ9T16EZSngQxNevsil-txb3xpEC4RKIE"
DB_ROOT = "https://chains-app-f38f8-default-rtdb.firebaseio.com"
HEADERS = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}

# If the new snapshot has fewer than this fraction of the previous snapshot's
# playRounds count, treat it as a possible data-loss event and warn loudly
# (but still save -- see note above).
DROP_WARN_THRESHOLD = 0.5


def post_json(url, payload, timeout=30):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=HEADERS, method="POST"
    )
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace"))


def get_json(url, timeout=30):
    req = urllib.request.Request(url, headers=HEADERS)
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace"))


def get_anon_id_token():
    resp = post_json(
        f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY}",
        {"returnSecureToken": True},
    )
    return resp["idToken"]


def previous_play_rounds_count(backup_dir):
    """Best-effort read of the prior snapshot's playRounds count, for
    drop detection. Returns None if there's no prior snapshot to compare
    against (first-ever run, or file missing/unreadable)."""
    latest = backup_dir / "rounds-latest.json"
    if not latest.exists():
        return None
    try:
        prev = json.loads(latest.read_text(encoding="utf-8"))
        return len(prev.get("playRounds") or {})
    except Exception:
        return None


def main():
    backup_dir = Path("data/backups")
    backup_dir.mkdir(parents=True, exist_ok=True)

    try:
        token = get_anon_id_token()
    except Exception as e:
        print(f"  rounds backup FAILED: could not get anon auth token: {e}")
        return

    play_rounds = {}
    live_rounds = {}
    try:
        play_rounds = get_json(f"{DB_ROOT}/playRounds.json?auth={token}") or {}
    except Exception as e:
        print(f"  rounds backup FAILED: could not read /playRounds: {e}")
        return
    try:
        live_rounds = get_json(f"{DB_ROOT}/liveRounds.json?auth={token}") or {}
    except Exception as e:
        # liveRounds is non-critical (transient) - warn but keep going
        print(f"  WARNING: could not read /liveRounds: {e}")

    total = len(play_rounds)
    if total == 0:
        print("  WARNING: /playRounds is empty - skipping to avoid saving bad data")
        return

    prev_total = previous_play_rounds_count(backup_dir)
    if prev_total is not None and prev_total > 0 and total < prev_total * DROP_WARN_THRESHOLD:
        print(
            f"  *** WARNING: POSSIBLE DATA LOSS *** /playRounds dropped from "
            f"{prev_total} to {total} (more than {int((1 - DROP_WARN_THRESHOLD) * 100)}% "
            f"decrease) since the last backup. Saving this snapshot anyway (per "
            f"chains-firebase-backup skill), but this matches the known Firebase "
            f"rollback pattern in company/LESSONS_LEARNED.md (Issues #28/#39) and "
            f"should be investigated, not silently rotated over."
        )

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    snapshot = {
        "backed_up_at": datetime.now(timezone.utc).isoformat(),
        "source": "firebase chains-app-f38f8 /playRounds + /liveRounds",
        "playRounds": play_rounds,
        "liveRounds": live_rounds,
    }
    dated = backup_dir / f"rounds-{today}.json"
    dated.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    latest = backup_dir / "rounds-latest.json"
    latest.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    print(f"  rounds backup OK: {dated.name} | {total} playRounds, {len(live_rounds)} liveRounds")


if __name__ == "__main__":
    main()
