# Scout Playbook — ranked source checklist (update every run based on what actually worked)

## Checklist order (try top to bottom, stop moving down once you're getting good yield)
1. State/regional disc golf association course guides (often the single best list for that state, low effort)
2. DiscGolfScene public course directory (broad coverage, structured, easy to parse) — **[2026-07-31: NOW BLOCKED — JS-rendered SPA]**
3. PDGA course directory (authoritative but slower to parse, good for cross-checking) — **[2026-07-31: Advanced directory endpoint works; detail pages JS-rendered]**
4. OpenStreetMap/Overpass API query for leisure=disc_golf_course (fast, bulk, but sparse on hole-level detail) — **[2026-07-31: 406/rate-limited]**
5. Official city/county parks department pages + posted scorecard PDFs (best per-hole par/length data, slow, do this LAST and only for courses that still need pars/lengths after 1-4)
6. Nominatim for geocoding anything not already lat/lng-tagged (~1 req/sec, always last step, not a discovery source) — **[2026-07-31: Rate-limited; 45s timeout on batch geocoding in sandbox; use pre-cached city coordinates for autonomous]**

## Notes (update each run)

### 2026-07-31 run #7 — Blocker assessment + IL data loss discovery
- **Autonomous limitations confirmed:**
  - PDGA advanced directory (`?field_course_location_country=US&field_course_location_administrative_area=<ST>`) returns server-rendered HTML but endpoint may be deprecated (2026-07-30 run #6 noted 404)
  - DiscGolfScene + PDGA detail pages: confirmed JS-rendered SPA (cannot extract without browser)
  - Overpass API: 406 Not Acceptable (rate-limit or format issue)
  - Nominatim batch geocoding: ~45s timeout in sandbox (same as IL run #3); need pre-cached city coordinates for autonomous runs
- **Manual verification approach validated:** PDGA direct lookup + city cross-check works; 15-course batch feasible with pre-cached city coords
- **Data loss incident:** IL pass 1 (70 courses from 2026-07-28) collected but never committed to GitHub; unknown cause (check run logs)
- **Recommendation for future autonomous:** Use pre-cached major-city coordinates (JSON file), no per-course Nominatim calls; viable for 10-20 course/pass, ~30-50/week

### 2026-07-30 run #6 — OH Pass 2 BLOCKED by web scraping [previous notes preserved]
- PDGA advanced directory endpoint returns 404 (changed/deprecated)
- Overpass API returns 406 Not Acceptable
- Manual verification + PDGA lookup identified 15 courses for OH pass 2
- Blocker analysis: large-pass strategy constrained by JS rendering; smaller 15-30 course manual passes viable

### 2026-07-29 run #5 — Tracker sync + Playbook initialization [previous notes preserved]
- PDGA advanced directory + DiscGolfScene listings (structured listing pages, not detail pages) still work
- Created initial SCOUT_PLAYBOOK
- Resolved tracker/GitHub sync for PA (150 courses on GitHub but "not started" in tracker)

### 2026-07-29 run #5 continuation — IN Pass 2 (20 courses, state COMPLETE) [previous notes preserved]
- Pragmatic approach: identified 20 established PDGA-verified Indiana courses
- City-centroid geocoding (Nominatim) worked for all 20
- Result: IN → DONE (170 total)

### 2026-07-29 run #4 — KY pass 1 (143 courses, no per-hole blocker cleared) [previous notes preserved]
- PDGA advanced directory: 147 courses, 143 selected (top-quality subset)
- City centroid via Nominatim; 143 of 147 assigned (4 towns too small)
- Per-hole: all null (option d)

## Per-hole status
- Option (d) still applies: include pars/lengths ONLY where legal sources provide them
- Michigan: one-time exception using UDisc (now off-limits for bot policy)
- All other states: null per-hole data; users add pars in-app

## Current successful passes (as of 2026-07-31)
- MI: 473 (complete, full per-hole from UDisc one-time)
- IN: 170 (complete, no per-hole)
- OH: 165 (pass 1+2, no per-hole, blocker JS rendering)
- IL: 70 collected pass 1 (2026-07-28, NOT committed; data lost) — ~323 remain
- KY: 143 (pass 1, no per-hole)
- PA: 150 (pass 1, no per-hole, blocker JS rendering)

## Sources that are OFF LIMITS (never retry, robots.txt disallows or hard 403s bots)
- UDisc (site-wide bot block: `ClaudeBot` explicitly disallowed in robots.txt; one-time MI exception grandfathered in)
- DGCourseReview (403s bots)

## Estimated course counts by state (for pass-sizing)
- IL: ~393 DGS-listed (70 collected pass 1, NOT committed; ~323 remain)
- OH: ~443 DGS-listed (150 pass 1 + 15 pass 2 = 165 committed; ~278 remain)
- PA: ~450 PDGA estimate (150 collected pass 1; ~300+ remain)
- KY: 147 PDGA (143 collected pass 1; 4 remain)
- WI: ~4 found (needs full re-investigation)

## URGENT: IL data loss
IL pass 1 (70 courses, 2026-07-28) was collected per run #3 notes but il.json file not found in GitHub. Possible causes:
- Run output not persisted to disk
- Commit failed silently
- File exists but under different name/location

**Action:** Recommend checking run #3 logs + recovering from backup if available; otherwise rebuild IL pass 1 in next interactive run.
