# chains-dgpt-data — schedule, results, field, catalogs, backups

**What this is:** the data the Chains app reads from GitHub (raw URLs). Python collectors run on GitHub Actions.

**Workflows (`.github/workflows/`)** — only three, on purpose:
- `collect.yml` — every 15 min: season schedule, registered field for the next event, final results per event, news,
  videos, player list.
- `backup.yml` — daily snapshot of the league database and Go Throw rounds into `data/backups/` (never pruned).
- `update-discs.yml` — weekly disc catalog refresh.
The live-scoring and draft/scoring workflows were removed on 2026-10-20: that work belongs to the Railway engine
(`chains-poller`) and having copies here made two programs fight over the same data.

**Data (`data/`)**
- `season.json` — the schedule (event number ↔ PDGA event id ↔ dates). Everything keys off this. Keep it complete for
  the whole season or the app goes blind after the last listed event.
- `field.json` — registered MPO players for the next event (the pick dropdown).
- `events/<pdgaId>-MPO.json` — final results + stats per event, every year back to 2016. **Historical record — keep.**
- `events-2025/` — last season. `season-20XX.json` — older seasons.
- `courses.json` (Michigan, with hole pars/lengths), `courses/<state>.json`, `courses-index.json` — the course catalog
  built by the data scout (see `SCOUT_PLAYBOOK.md`, `COURSE_EXPANSION.md`).
- `discs.json` — ~1,200 discs by brand/type (In the Bag).
- `backups/` — league snapshots by date; `latest.json` is the newest.

**Scripts** — `collect_*.py`, `backup_*.py`, `update_discs.py`, `list_events.py`. Each is standalone, stdlib only.

**Archive** — `archive/2026-09-agent-company/`: the September multi-agent experiment's docs. Reference only, not live.
