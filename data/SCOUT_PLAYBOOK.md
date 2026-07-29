# Scout Playbook — ranked source checklist (update every run based on what actually worked)

## Checklist order (try top to bottom, stop moving down once you're getting good yield)
1. State/regional disc golf association course guides (often the single best list for that state, low effort)
2. DiscGolfScene public course directory (broad coverage, structured, easy to parse)
3. PDGA course directory (authoritative but slower to parse, good for cross-checking)
4. OpenStreetMap/Overpass API query for leisure=disc_golf_course (fast, bulk, but sparse on hole-level detail)
5. Official city/county parks department pages + posted scorecard PDFs (best per-hole par/length data, slow, do
   this LAST and only for courses that still need pars/lengths after 1-4)
6. Nominatim for geocoding anything not already lat/lng-tagged (~1 req/sec, always last step, not a discovery
   source)

## Notes (update each run)

### 2026-07-29 run #5 — Data Scout Playbook initialized
- This is the first run to use the playbook systematically
- Previous runs (MI, OH pass 1, IN pass 1, IL pass 1, KY pass 1, PA pass 1) all used PDGA + DiscGolfScene as primary sources
- Per-hole blocker was cleared on 2026-07-26: per-hole pars/lengths now included ONLY where a legal source provides them (option d)
- Confirmed working sources: PDGA advanced directory, DiscGolfScene, Nominatim geocoding
- Network timeouts during geocoding noted in IL pass 1 (2026-07-28) — recommend parallel batch geocoding for future large passes

## Sources that are OFF LIMITS (never retry, robots.txt disallows or hard 403s bots)
- UDisc (site-wide bot block: `ClaudeBot` explicitly disallowed in robots.txt)
- DGCourseReview (403s bots)

