# Course data — where it comes from, what we may keep

Goal: every disc golf course, with a map, without copying anyone's database. Each record in
`data/courses.json` carries provenance (`source_*` flags, `attribution`). If a source isn't listed here, it's not in.

| Source | What | Licence / terms | Status |
|---|---|---|---|
| **OpenStreetMap** (Overpass) | ~2,800 courses worldwide, ~11,000 mapped tees/baskets (taginfo, Oct 2026) | ODbL — attribution "© OpenStreetMap contributors"; a published database derived from it stays ODbL | **Automated weekly** (`collect_osm_courses.py` → `merge_courses.py`) |
| **US Census state boundaries** | which state a point is in | public domain | cached once (`data/sources/us_states.json`) |
| **Players in Chains** ("add your course", mark tee/basket, pars, lengths) | the rest — this is how every course eventually gets a real map | ours; the mapper gets "Pioneer" on the course for good | in-app (courseGeo), exported nightly by the backup |
| **PDGA course directory** | ~15,000 US courses: name, city, holes, par, year | PDGA terms restrict automated collection; **ask for a licence** (affiliate/data agreement) | email drafted below — Will sends |
| **DiscGolfMetrix API** | courses, layouts, some hole data (strong in Europe) | API by permission | ask |
| **Government open data** (county/city GIS park layers) | park features incl. some disc golf | public domain / open | opportunistic, per county |
| **Kaggle "PDGA US courses" (CC0)** | a 2021 scrape of PDGA | uploader's CC0 can't cover PDGA's rights — use only to cross-check names/locations, never import | reference only |
| **UDisc** | best data there is | their users' contributions; terms forbid automated collection | **not used** — by decision |
| **Google Places** (reviews, ratings, photos) | reviews/ratings per course | may be *displayed* live with a key; may **not** be stored beyond 30 days except `place_id` | later: store `place_id` only, fetch at view time |
| **Satellite imagery** | Esri World Imagery (today via the public tile server) | fine for development; for the shipped app use Esri Location Platform (free tier, API key) or MapTiler/Mapbox free tier | on the to-do list before App Store |

## Emails to send (Will)
**PDGA** (info@pdga.com, subject "Course directory data licence for a community app"): who we are, what Chains is,
that we'd like a licence or API access to the course directory (name, location, holes, par) with attribution and
a link back to each course page, non-commercial today, and ask what their affiliate/data terms are.
**UDisc** (support@udisc.com): same shape — ask whether any course-data partnership or API exists. Expect "no";
asking costs nothing and documents good faith.
**DiscGolfMetrix** (via discgolfmetrix.com contact): API key request for course/layout data.
