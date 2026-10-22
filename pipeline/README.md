# pipeline/ — the course-data side project

Runs on GitHub Actions on a schedule. No AI, no laptop. Pulls open data, merges it into the app catalog with
provenance, and keeps per-course geometry files for the app's maps.

```
pipeline/collect_osm_courses.py   OpenStreetMap → data/sources/osm/{courses,nodes,meta}.json   (US, ~8 min)
pipeline/merge_courses.py         sources → data/courses.json (+ data/geo/osm/<courseId>.json)
pipeline/SOURCES.md               every source, its licence, what we may keep
.github/workflows/course-pipeline.yml   Sundays 08:00 UTC, or Run workflow
```

Rules: hand-made data in the catalog always wins; nothing is ever deleted by the pipeline; every touched record
says where it came from. New courses arrive with `needs_review: true` and show in the app as community courses
to help map. Local test: `python3 pipeline/collect_osm_courses.py MI,OH && python3 pipeline/merge_courses.py`.
