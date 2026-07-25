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
"""
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_KEY = "AIzaSyAZ9T16EZSngQxNevsil-txb3xpEC4RKIE"
DB_ROOT = "https://chains-app-f38f8-default-rtdb.firebaseio.com"
HEADERS = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}


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
