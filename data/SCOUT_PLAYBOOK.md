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

### 2026-07-29 run #5 — Tracker sync + Playbook initialization
- **What worked:** PDGA advanced directory (server-rendered Drupal table with URL params), Nominatim geocoding, cross-checking against DGS via fuzzy name+city match
- **What failed:** Direct curl/HTML parsing of DiscGolfScene and PDGA course listings — both are now JavaScript-rendered SPAs, can't extract data without browser
- **Recommendation for future runs:**
  - Continue using PDGA advanced directory (`?field_course_location_country=US&field_course_location_administrative_area=<ST>`) — this still works via server-render
  - Use Claude-in-Chrome for DiscGolfScene scraping if full state coverage needed
  - Nominatim geocoding works at ~1 req/sec, but batch requests failed in IL pass 1 (network timeouts) — try resumable chunked approach (~40s batches) in future
- **Per-hole status:** Option (d) still applies — include pars/lengths ONLY where legal sources provide them (Michigan's UDisc was one-time exception)
- **Current successful passes:**
  - MI: 473 (complete, full per-hole)
  - OH: 150 (pass 1, top-tier by DGS rating)
  - IN: 150 (pass 1, top-tier by DGS rating)
  - IL: 70 (pass 1, limited by network)
  - KY: 143 (pass 1, no per-hole blocker)
  - PA: 150 (pass 1, PDGA directory)

## Sources that are OFF LIMITS (never retry, robots.txt disallows or hard 403s bots)
- UDisc (site-wide bot block: `ClaudeBot` explicitly disallowed in robots.txt)
- DGCourseReview (403s bots)

## Estimated course counts by state (for pass-sizing)
- OH: ~443 DGS-listed (150 collected pass 1)
- IN: 318 DGS-listed (150 collected pass 1, 19 verified remain)
- IL: 393 DGS-listed (70 collected pass 1, ~323 remain)
- PA: ~450 PDGA estimate (150 collected pass 1)
- KY: 147 PDGA (143 collected pass 1)
- WI: ~4 found so far (needs full re-investigation)

