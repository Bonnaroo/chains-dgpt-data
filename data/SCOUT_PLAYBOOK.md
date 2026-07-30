# Scout Playbook — ranked source checklist (update every run based on what actually worked)

## Checklist order (TRY TOP TO BOTTOM, stop moving down once you're getting good yield)

**FOR INTERACTIVE/BROWSER RUNS (Claude-in-Chrome available):**
1. DiscGolfScene public course directory — JavaScript-rendered, needs browser
2. PDGA course detail pages (individual course lookup) — JavaScript-rendered, needs browser
3. State/regional disc golf association course guides — often the single best list, HTML-parseable
4. Official city/county parks department pages + scorecard PDFs

**FOR AUTONOMOUS/SANDBOX RUNS (curl/Python only):**
1. Manual PDGA verification (direct course lookup by slug/ID) + city cross-check — slow but 100% accurate
2. State/regional disc golf association course guides (if HTML) — low effort if available
3. Nominatim geocoding for verified course names (~1 req/sec, always last step)
4. OpenStreetMap/Overpass API (disc_golf_course tag) — works intermittently, may rate-limit

## Notes (update each run)

### 2026-07-30 run #6 — Web scraping limitations confirmed
- **PDGA advanced directory:** Endpoint returns 404 (endpoint deprecated/moved)
- **DiscGolfScene:** Confirmed JS-rendered SPA (cannot extract via curl)
- **Overpass API:** Returns 406 (rate limit or query format incompatible with sandbox)
- **Solution:** For large passes (150+), use Claude-in-Chrome interactive scraping
- **Autonomous workaround:** Stick to manual verification passes (15-20 courses/run) via direct PDGA lookup + city geocoding
- **Success rate:** Manual passes are small but 100% verified; suitable for weekly incremental updates

### 2026-07-29 run #5 — Tracker sync + Playbook initialization
- **What worked:** PDGA advanced directory (server-rendered Drupal table with URL params), Nominatim geocoding, cross-checking against DGS via fuzzy name+city match
- **What failed:** Direct curl/HTML parsing of DiscGolfScene and PDGA course listings — both are now JavaScript-rendered SPAs, can't extract data without browser
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

