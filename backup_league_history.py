#!/usr/bin/env python3
"""
Chains - real-time pick change history.
Runs frequently (via scheduled Watcher task). Compares the live /league
picks against the last known state; any time a pick actually changes,
appends a permanent, timestamped entry to data/picks_history.jsonl
showing exactly what changed (member, tournament, field, old -> new).
Also refreshes data/backups/latest.json every run so there's always a
current full snapshot, independent of the once-daily permanent backup.

State tracking file: data/last_known_picks.json (committed, not secret).
"""
import json, os, sys
from datetime import datetime, timezone

FIREBASE = "https://chains-fantasy-default-rtdb.firebaseio.com/league.json"

def fetch_live(token):
    import urllib.request
    url = FIREBASE + (f"?access_token={token}" if token else "")
    return json.loads(urllib.request.urlopen(url, timeout=30).read())

def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def diff_picks(old_keys, new_keys, now_iso):
    entries = []
    for vk, node in (new_keys or {}).items():
        if not vk.startswith("picks~46~"):
            continue
        t = vk.replace("picks~46~", "")
        try:
            new_arr = json.loads(node["v"])
        except Exception:
            continue
        old_node = (old_keys or {}).get(vk)
        try:
            old_arr = json.loads(old_node["v"]) if old_node else []
        except Exception:
            old_arr = []
        old_by_member = {r["m"]: r for r in old_arr if r.get("m")}
        for row in new_arr:
            m = row.get("m")
            if not m:
                continue
            old_row = old_by_member.get(m, {})
            for field in ("p1", "s1", "p2", "s2"):
                old_val = old_row.get(field)
                new_val = row.get(field)
                if old_val != new_val:
                    entries.append({
                        "ts": now_iso, "tournament": t, "member": m,
                        "field": field, "old": old_val, "new": new_val,
                    })
    return entries

def main():
    token = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("FANTASY_ADMIN_TOKEN", "")
    live = fetch_live(token)
    new_keys = live.get("keys", {})
    old_state = load_json("data/last_known_picks.json", {})
    old_keys = old_state.get("keys", {})
    now_iso = datetime.now(timezone.utc).isoformat()

    changes = diff_picks(old_keys, new_keys, now_iso)

    if changes:
        with open("data/picks_history.jsonl", "a") as f:
            for c in changes:
                f.write(json.dumps(c) + "\n")
        print(f"  {len(changes)} pick change(s) logged.")
    else:
        print("  no pick changes since last check.")

    save_json("data/last_known_picks.json", {"checked_at": now_iso, "keys": new_keys})
    save_json("data/backups/latest.json", {"backed_up_at": now_iso, "source": "firebase /league (auto, every watcher cycle)", "data": live})

if __name__ == "__main__":
    main()
