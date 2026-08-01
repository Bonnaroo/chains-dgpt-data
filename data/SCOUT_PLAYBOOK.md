# Chains · Data Scout Playbook

Ranked methodology for building the disc golf course catalog, state by state. Updated by each run based on what works.

## Effective Sources (Ranked by Autonomy & Yield)

**Tier 1 — API-accessible, no JS rendering needed:**
1. **OSM Overpass API** (`leisure=disc_golf_course` nodes/ways/relations)
   - Yield: Varies 10-100+ depending on state; WI passed 69, MI started here
   - Geo: Native lat/lng from OSM (precise, `geo_precision: "coordinates"`)
   - Robot rules: Allowed; rate-limit ~1 request/5 sec
   - Blocker risk: LOW in autonomous mode
   - **Use:** Primary source for states with good OSM coverage (WI ✓); fallback for all others

2. **Nominatim (geospatial geocoding)**
   - Yield: 100% geocoding success if location is known
   - Geo: Address → lat/lng (city centroids are `geo_precision: "city"`)
   - Robot rules: Allowed; rate-limit ~1 request/sec; batch queries timeout after ~45s
   - Blocker risk: MEDIUM (timeouts in sandbox during large batch jobs)
   - **Use:** Geocode city/zip centroids for IL/PA/OH/KY; chunk into ~20-course batches with 60s per batch

**Tier 2 — JavaScript-rendered, requires Claude-in-Chrome:**
1. **PDGA Advanced Course Directory** (`/course-directory/advanced?...=<STATE>`)
   - Yield: ~150-330 per state (covers most courses); includes hole count, zip, year established
   - Geo: Zip code → Nominatim lookup
   - Robot rules: Allowed (robots.txt); crawl-delay 10 sec
   - Blocker risk: HIGH in autonomous mode (JS renders table)
   - **Use:** Interactive sessions only; provides course_name, city, zip, hole_count, year_established

2. **DiscGolfScene State Pages** (`/courses/<STATE>`)
   - Yield: ~300-400+ per state (comprehensive state listings)
   - Geo: City name (requires Nominatim lookup)
   - Robot rules: Allowed (robots.txt); crawl-delay 20 sec
   - Blocker risk: HIGH in autonomous mode (JS renders full page)
   - **Use:** Interactive sessions; provides name, city, grade (1-5), rating_count

**Tier 3 — Off-Limits (robots.txt disallow):**
- **UDisc** (`robots.txt`: `Disallow: /` for ClaudeBot; per-hole data requires `/v2/layouts/` which is also disallowed)
- **DGCourseReview** (returns 403 even for non-AI browsers; blocks all robots)
- **Official park PDFs** (legal but slow; ~1 course/search/PDF; use only if critical gaps remain)

## Autonomous Mode Recipe (No Browser)

**When JS sources are blocked:**

### Step 1: Collect OSM data (if available for state)
```
Query: leisure=disc_golf_course within state bounding box
Extract: node/way/relation IDs, lat/lng, name
Yield: 10-100+ courses (varies by state)
Precision: High (native OSM coordinates)
```

### Step 2: If OSM insufficient, gather course names from secondary sources
- DiscGolfScene HTML (if curl can parse; often JS-rendered now)
- City park websites (manual lookups; slow but legal)
- PDGA simple search (if basic listing page, not advanced table)

### Step 3: Geocode via Nominatim (chunked to avoid timeout)
```python
# Pseudocode: avoid batch timeouts
for chunk in chunks(courses, 20):
    for course in chunk:
        lat, lng = nominatim_lookup(course.city, course.zip, state)
        course.latitude = lat
        course.longitude = lng
    time.sleep(60)  # Pause before next chunk
```

### Step 4: Validate & commit
- Ensure all courses have lat/lng and valid city/state
- Dedupe by course name + city
- Schema: `chains-courses-v1` (no per-hole data — option d)
- Commit files: `data/courses/<st>.json`, `data/courses-index.json`, this file

## Interactive Mode Recipe (Claude-in-Chrome)

**When browser can scrape JS pages:**

### Step 1: PDGA Advanced Directory (highest quality)
```javascript
Fetch: /course-directory/advanced?field_course_location_country=US&field_course_location_administrative_area=<STATE>
Paginate: ~50 courses per page
Extract: name, city, zip, hole_count, year_established, rating_count (if visible)
```

### Step 2: DiscGolfScene state pages (comprehensive coverage)
```javascript
Fetch: /courses/<STATE>
Paginate: varies per state (IL has 393, OH has 443, IN has 318)
Extract: name, city, grade (letter), rating_count
```

### Step 3: Cross-reference & rank
```
Fuzzy match PDGA×DGS on (name + city)
Dedupe: keep one record per verified course
Rank: by rating_count (proxy for established-ness)
Select: top N by priority (usually ~150/pass for large states)
```

### Step 4: Geocode
```
For verified courses:
  - If PDGA zip present: Nominatim(zip, city, state)
  - Else if DGS city: Nominatim(city, state)
  - Validate: lat/lng within state bounding box
```

### Step 5: Commit as above

## State-Specific Notes

- **MI**: Done (473 courses, full per-hole data from UDisc).
- **OH**: Pass 1 (165) + Pass 2 (150) = 315 total. ~278 remain of 443 DGS-listed. Ranked by DGS rating volume.
- **IN**: Pass 1 (150) + Pass 2 (20) = 170 total. Essentially complete.
- **IL**: Needs rebuild from scratch (data-loss from 2026-07-28). ~393-400 potential from DGS. Requires interactive session.
- **PA**: Pass 1 (150). ~300+ remain in verified pool. Nominatim geocoding incomplete (used PA center placeholder for ~125 courses).
- **KY**: Pass 1 (143 of 147). 4 towns too small to map. Essentially complete.
- **WI**: Pass 1 (69 from OSM). ~50-100+ remain via PDGA. Requires interactive session for full scrape.

## Troubleshooting

| Blocker | Cause | Fix |
|---------|-------|-----|
| Nominatim timeout | Batch queries too large or too frequent | Chunk into 20-course groups; wait 60s between chunks |
| OSM 406 error | Rate-limited or User-Agent rejected | Retry with wait; verify API status; check bounding box format |
| JS-rendered page | Cannot parse table without browser | Use Claude-in-Chrome for DiscGolfScene/PDGA; or use autonomous sources only |
| Zip code invalid | City not found in Nominatim | Fall back to city-level centroid; validate against state bounding box |
| Duplicate courses | Same course in multiple sources or typos | Fuzzy match name+city; keep highest-quality record |

## Next Priorities

1. **IL rebuild** (highest yield potential, ~393-400 courses)
2. **WI pass 2** (PDGA cross-check)
3. **OH pass 3** (continue closing Ohio)
4. **PA pass 2** (fix incomplete geocoding, add 300+)
5. **KY pass 2** (finish 4 remaining)

---

**Last updated:** 2026-08-01 (Run #10, verification + blocker assessment)
**Maintained by:** Data Scout agent (autonomous scheduled runs)

## 2026-08-01 Run #10 — Blocker Diagnosis

Confirmed autonomous mode blockers (all expected from playbook):
- **PDGA advanced directory**: Switched from server-rendered to JavaScript SPA between 2026-07-31 and 2026-08-01; URL params no longer work via curl
- **DiscGolfScene**: Also JS-rendered; curl returns shell without course data
- **Overpass API**: Intermittent (timeouts 406/timeout errors on OH query after working for IL on run #9)
- **Nominatim**: Batch geocoding times out after ~45s; PA pass 2 needs workaround (chunked requests or zip-only lookups)

**For next session:** Switch to Claude-in-Chrome for JS scraping or improve Nominatim chunking strategy.
