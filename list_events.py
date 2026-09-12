#!/usr/bin/env python3
"""Print the PDGA event ids the collector should refresh, one per line:
every event in data/season.json whose start_date has arrived (UTC), plus any
extra ids in events.txt. Used by .github/workflows/collect.yml so a new
tournament is picked up automatically each week."""
import json, datetime, pathlib

today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
ids = []
for e in json.load(open("data/season.json", encoding="utf-8")).get("events", []):
    if e.get("event_id") and (e.get("start_date") or "9999-99-99") <= today:
        ids.append(str(e["event_id"]))
p = pathlib.Path("events.txt")
if p.exists():
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and line not in ids:
            ids.append(line)
print("\n".join(ids))
