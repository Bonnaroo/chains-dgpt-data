# Course record format — what to hand the app

Drop files into **`data/inbox/`** in `Bonnaroo/chains-dgpt-data` (any name, `.json`, `.jsonl` or `.csv`).
The pipeline ingests them on every run (`ingest_inbox.py`), merges into `data/courses.json`, writes the map files,
and moves the file to `data/inbox/done/`. The app pulls the catalog on its own; satellite imagery needs nothing
from you — any course with `lat`/`lng` gets imagery automatically, and any course with `geo` gets hole maps.

## Minimum (a course shows up in the app)
```json
{ "name": "Otterburn Disc Golf Park", "lat": 42.972629, "lng": -83.797976, "holes": 18,
  "state": "MI", "country": "US", "source": "pdga-license", "source_url": "https://...", "collected": "2026-10-22" }
```
`source` is required and must be one of: `osm`, `pdga-license`, `metrix-api`, `gov:<agency>`, `player`, `owner`
(course/park management gave it), `manual` (typed from a tee sign / your own visit). Records without a legal
`source` are skipped by the ingest — on purpose.

## Full record (everything the app can use)
```json
{
  "id": "mi-otterburn",                 // optional; made from state + name if missing
  "name": "Otterburn Disc Golf Park",
  "lat": 42.972629, "lng": -83.797976,  // course centre or hole 1 tee, decimal degrees
  "city": "Swartz Creek", "state": "MI", "country": "US", "county": "Genesee",
  "address": "1004 S Linden Rd, Swartz Creek, MI 48473",
  "holes": 18,
  "hole_pars":    [3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3],
  "hole_lengths": [229,220,259,216,250,300,280,310,265,290,245,280,300,320,260,275,250,194],   // feet
  "play_order": [2,3,4,5,6,7,8,9,1,10,11,12,13,14,15,16,17,18],   // only if the signed walk differs from 1..N
  "year": 2004, "fee": "free", "access": "public", "website": "https://...", "phone": "...",
  "hours": "dawn to dusk",
  "amenities": { "bathroom": true, "water": false, "dogs": true, "carts": false, "lit": false },
  "description": "Wooded back nine, open front nine…",
  "hole_notes": { "1": "OB road left", "7": "Mando right of the big oak" },
  "geo": {                               // per hole; lat,lng pairs; doglegs optional (fairway bends, in throw order)
    "1": { "tee": [42.97301, -83.79842], "basket": [42.97242, -83.79811], "doglegs": [] },
    "2": { "tee": [42.97230, -83.79790], "basket": [42.97170, -83.79760], "doglegs": [[42.97200, -83.79800]] }
  },
  "layouts": [ { "name": "Long tees", "hole_pars": [...], "hole_lengths": [...], "geo": { ... } } ],   // optional extra layouts
  "photos": [],                          // not yet used; leave empty
  "source": "manual", "source_url": null, "collected": "2026-10-22", "collected_by": "will"
}
```
Rules: feet for lengths, decimal degrees for coordinates (6 decimals), hole keys are strings `"1"…`, arrays are in
hole-number order (not play order), `null` for unknown, never guess a coordinate.

## Bulk
- **`.jsonl`** — one record per line (best for thousands).
- **`.csv`** — two files are fine: `courses.csv` (columns = the top-level fields; `hole_pars`/`hole_lengths` as
  `3|3|3…`) and `holes.csv` (`course_id, hole, par, length_ft, tee_lat, tee_lng, basket_lat, basket_lng, doglegs`
  with doglegs as `lat,lng;lat,lng`).

## How Otterburn got in
Will's 2026-10-21 data pack (otterburn.json + hole screenshots → typed into this format) seeded
`data/courses.json` and `data/geo/mi-otterburn.json`; the app also stores player-marked tees/baskets in
Firebase `courseGeo/{courseId}` which override the file. Satellite imagery is Esri World Imagery tiles fetched
by coordinate — nothing is stored.
