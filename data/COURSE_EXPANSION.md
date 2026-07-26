# Chains · Course Expansion — Progress & Queue

Automated state-by-state disc golf course collection for `chains-dgpt-data`
(data/courses.json = MI, data/courses/<st>.json = everything else).
One state per scheduled run. Read this file first; pick the next
uncollected state; update it when done.

## ✅ 2026-07-26 run — OH pass 1 (unblocked, 150 courses)

**Blocker resolved by task-spec change:** the scheduled task now says per-hole
pars/lengths go in "ONLY where a legal source provides them (otherwise leave
blank — the app lets users add pars)". That is option (d) from the 2026-07-25
block, so the systemic per-hole blocker no longer gates collection. OH and IN
are therefore back to collectible; this run did **Ohio pass 1**.

**What was built (150 courses, `data/courses/oh.json`):**
- **DiscGolfScene** public state directory (robots: allowed, crawl-delay 20 —
  one listing page has all 443 OH courses): name, city, letter grade, rating count.
- **PDGA advanced course directory** (`/course-directory/advanced?...=OH`,
  robots: allowed, crawl-delay 10): server-rendered Drupal table — 331 OH
  courses with name, city, **hole count**, zip, year established. NOTE: this
  listing view has hole counts even though the per-course SPA pages don't —
  the 07-25 runs only checked the detail pages, so this was missed.
- **Cross-check:** fuzzy name+city match PDGA×DGS → 283 verified courses.
  Ranked by DGS rating volume (established-ness proxy), took top 150
  (~150/run cap) → **OH is Partial, ~133 verified candidates remain**.
- **Geo:** OSM/Overpass (only 29 named `leisure=disc_golf_course` in OH) gave
  13 exact coords after validating each against its Nominatim zip centroid
  (<=35 km, catches false name matches); the other 137 use Nominatim **zip
  centroids** (`geo_precision: "zip"`), all validated to Ohio. Nominatim
  structured query needs `country=us` (`country=USA` + state returns []).
- **Per-hole:** all 150 have `hole_pars`/`hole_lengths` = null, per option (d).
  UDisc & DGCourseReview remain off-limits (robots.txt, re-confirmed 07-25).

**Files committed this run:** `data/courses/oh.json`,
`data/courses-index.json` (new), `data/Chains Course Catalog.xlsx` (tracker:
OH → Partial 150; Courses tab +150 rows), this file.

**Next pass:** OH pass 2 (remaining ~133 verified of 443 DGS-listed), then IN
(also unblocked — same recipe applies).

## ⚠️ 2026-07-25 run — BLOCKED, read before continuing

This run attempted **Ohio** and hit a methodology problem that will block
**every** future state, not just OH, so it's flagged here instead of buried
in a per-state note.

**What happened:** The Michigan file's `_meta.note` says its per-hole data
came from "UDisc current layout." I confirmed why that worked and why it
won't work again: UDisc's course pages don't expose hole-by-hole par/
distance in the static HTML, but their internal `/v2/layouts/<id>.data`
route does (a turbo-stream payload) — I fully reverse-engineered the
encoding and validated it byte-for-byte against Mott Park's real 18-hole
data (par 56 / 6,766 ft, exact match). Technically it works.

**Why I didn't use it:** `udisc.com/robots.txt` explicitly disallows
`ClaudeBot` from the entire site (`Disallow: /`), alongside GPTBot, CCBot,
and other AI crawlers. It separately disallows *everyone* (not just AI
bots) from the exact pages this needs: `/courses/*/v2/layout` and
`/courses/*/layouts/*/caddie-book`. Scripting around that — even via the
browser instead of the sandbox — is circumventing a site's explicit,
bot-specific policy, so I stopped rather than build the pipeline on it.
That wasn't a policy in place (or wasn't checked) when MI was built.

**What I checked instead, for Ohio (443 candidate courses pulled from
DiscGolfScene's public directory, which has no such restriction):**
- DiscGolfScene course/about pages: no structured hole tables, only
  aggregate stats (total length, hole-count buckets).
- PDGA course directory pages: no hole-by-hole par/distance data, just
  description + address + totals.
- DGCourseReview: blocks robots.txt itself with a 403 — off-limits.
- Official park/city sites (Canton, Hilliard, Green, etc.): only publish
  aggregate course stats; Hilliard's site 403'd scripted requests outright.
- Net result: 0 courses with a verifiable full 18-hole par+distance set
  from a source I could compliantly automate. Below the 20-course quality
  bar, so **nothing was built or committed for OH.**

**Ohio status:** left in the queue, unstarted (name/city/rating list for
443 candidates is sitting in `/tmp/oh_dgs_list.json` in this run's
sandbox if a future run wants a head start — not persisted anywhere
durable, so treat it as disposable).

**Recommendation for Guillermo:** the state-by-state expansion needs a new
per-hole data source before another run can add real course counts. Options
worth considering: (a) UDisc has an official partner/export API — worth
asking them directly rather than scraping; (b) if you have your own UDisc
account, an export of layouts you've personally saved/played is yours to
use and isn't a bot-crawl question; (c) lean fully on official park PDFs
found one course at a time (slow, low yield based on this run's sample);
(d) accept course entries without per-hole data for non-MI states and
change the in-app handling instead of dropping them. Happy to build
whichever path you pick — just flag it back to this file or in chat.

## ⚠️ 2026-07-25 run #2 (IN) — same blocker, confirmed systemic

Per the queue, this run moved to **Indiana** (OH is still blocked, not
done, so it stays in place and IN was picked next). Before repeating the
full OH investigation, I re-verified the two load-bearing facts from the
block above, since if they still hold, the blocker isn't state-specific
and doesn't need to be re-litigated per state:

- `udisc.com/robots.txt` **still** disallows `ClaudeBot` (`Disallow: /`)
  site-wide, confirmed by direct fetch today.
- PDGA course directory course pages are a JS single-page app — fetched
  `pdga.com/course-directory/course/holliday-park` (a real Indianapolis
  course) both via plain HTTP and via a JS-rendering browser; both return
  only the search/map shell, no hole-by-hole par or distance for any
  course. This matches the OH finding exactly, just double-checked with a
  browser this time instead of relying on the static-HTML check alone.

**Conclusion:** the blocker is about the source landscape, not Ohio
specifically. It will reproduce for IN, IL, WI, KY, PA, NY, and every
other state under the current recipe. Re-running the identical
DGS/PDGA/DGCourseReview/official-site checks state-by-state would just
burn scheduled runs to re-confirm the same thing. **Nothing was built or
committed for IN** — same reasoning as OH (0 courses clear the
verifiable-hole-data bar).

**Suggestion:** the course-expansion scheduled task should probably be
paused (or switched to a "check for a decision" no-op) until Guillermo
picks one of the four options listed in the OH block above. Otherwise
each future run will independently re-derive "still blocked" without
adding real data. Left the schedule itself untouched since that's a
config change outside this task's scope — flagging it here instead.

## Recipe (unchanged)
See scheduled task definition for the full spec. Schema: `chains-courses-v1`.
Sources: PDGA directory, DiscGolfScene, publicly-viewable UDisc pages
*(see block above — currently paused)*, official scorecards. Geocode via
Nominatim, 1 req/sec, state+city validated. Drop courses with no per-hole
data. Cap big states at ~150 most established courses per pass.

## Queue

**Priority order:** OH, IN, IL, WI, KY, PA, NY → TX, CA, NC, MN, CO, OR,
WA, TN, GA, FL, AZ, MO, IA, KS → rest alphabetically.

| State | Status | Count | Date | Notes |
|---|---|---|---|---|
| MI | done | 473 | 2026-06-20 | Original build, see data/courses.json _meta |
| OH | partial | 150 | 2026-07-26 | Pass 1: top 150 of 283 PDGA×DGS verified (443 DGS-listed). No per-hole data (option d). Continue next pass. |
| IN | not started | — | — | Unblocked 2026-07-26 (option d adopted in task spec) — use OH recipe |
| IL | not started | — | — | |
| WI | not started | — | — | |
| KY | not started | — | — | |
| PA | not started | — | — | |
| NY | not started | — | — | |
| TX | not started | — | — | |
| CA | not started | — | — | |
| NC | not started | — | — | |
| MN | not started | — | — | |
| CO | not started | — | — | |
| OR | not started | — | — | |
| WA | not started | — | — | |
| TN | not started | — | — | |
| GA | not started | — | — | |
| FL | not started | — | — | |
| AZ | not started | — | — | |
| MO | not started | — | — | |
| IA | not started | — | — | |
| KS | not started | — | — | |
| (remaining states alphabetically) | not started | — | — | AK, AL, AR, CT, DE, HI, ID, LA, MA, MD, ME, MS, MT, ND, NE, NH, NJ, NM, NV, OK, RI, SC, SD, UT, VA, VT, WV, WY |
