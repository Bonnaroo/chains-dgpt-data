#!/usr/bin/env python3
"""Fold the open sources into the app catalog (data/courses.json) with provenance, never losing hand-made data.

Rules
- Existing catalog entries are never deleted or renamed. Fields filled by a person in the app
  (hole_lengths, hole_pars, rating, hole_notes, amenities) always win over any source.
- An OSM course matches an existing course when it is within 300 m, or has the same normalised name within 2 km.
  Matched: add `osm` id, fill missing lat/lng/holes/website, set source_osm=true.
- Unmatched OSM courses with a name are added as new entries: id "osm-<type>-<id>", source_osm=true,
  needs_review=true (nobody has played them in Chains yet; the app shows them as "community course, help map it").
  Unnamed OSM courses are added only if they have real geometry (9+ baskets).
- Mapped tees/baskets (data/sources/osm/nodes.json) become data/geo/osm/<courseId>.json for every catalog course
  that has 9+ baskets within 1.5 km (ref= numbers assign holes; the rest are candidates to assign in the app).
- Attribution is carried on every record touched: "© OpenStreetMap contributors (ODbL)".

Run after collect_osm_courses.py:  python3 pipeline/merge_courses.py
"""
import json, math, os, re, datetime

CAT = "data/courses.json"; SRC = "data/sources/osm"; GEO = "data/geo/osm"
ATTR = "© OpenStreetMap contributors (ODbL)"


def dist_m(a, b):
    R = 6371000.0
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def norm(s):
    s = (s or "").lower()
    s = re.sub(r"\b(disc golf|dgc|dg|course|park|the)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def main():
    raw = json.load(open(CAT)); arr = raw if isinstance(raw, list) else raw.get("courses")
    osm = json.load(open(f"{SRC}/courses.json")); nodes = json.load(open(f"{SRC}/nodes.json"))
    by_osm = {c.get("osm"): c for c in arr if c.get("osm")}
    located = [c for c in arr if c.get("lat") is not None]
    added = matched = 0
    for o in osm:
        if o["osm"] in by_osm:
            c = by_osm[o["osm"]]
        else:
            c = None; best = 400
            for x in located:
                if abs(x["lat"] - o["lat"]) > 0.02 or abs(x["lng"] - o["lng"]) > 0.03: continue
                d = dist_m((x["lat"], x["lng"]), (o["lat"], o["lng"]))
                if d < 300 and d < best: c, best = x, d
                elif d < 2000 and o["name"] and norm(x.get("name")) == norm(o["name"]) and d < best: c, best = x, d
            if c is None:
                if not o["name"] and o["mapped"]["baskets"] < 9: continue
                c = {"id": "osm-" + o["osm"].replace("/", "-"), "name": o["name"] or "Disc golf course (unnamed on OpenStreetMap)",
                     "lat": o["lat"], "lng": o["lng"], "state": o.get("state"), "country": o.get("country") or "US",
                     "holes": o.get("holes") or (o["mapped"]["baskets"] if o["mapped"]["baskets"] >= 9 else None),
                     "city": (o.get("tags") or {}).get("addr:city"), "needs_review": True, "added": datetime.date.today().isoformat()}
                arr.append(c); located.append(c); added += 1
            else:
                matched += 1
        c["osm"] = o["osm"]; c["source_osm"] = True; c["attribution"] = ATTR
        for k_src, k_dst in (("holes", "holes"), ("website", "website"), ("operator", "operator"), ("fee", "fee")):
            if c.get(k_dst) in (None, "", 0) and o.get(k_src): c[k_dst] = o[k_src]
        if c.get("lat") is None: c["lat"], c["lng"] = o["lat"], o["lng"]
        c["osm_mapped"] = o["mapped"]
        by_osm[o["osm"]] = c
    # geometry files
    os.makedirs(GEO, exist_ok=True); geo_written = 0
    for c in located:
        mine = [n for n in nodes if abs(n["lat"] - c["lat"]) < 0.02 and abs(n["lng"] - c["lng"]) < 0.03 and dist_m((c["lat"], c["lng"]), (n["lat"], n["lng"])) < 1500]
        baskets = [n for n in mine if n["kind"] == "basket"]
        if len(baskets) < 9: continue
        holes = {}
        for n in mine:
            r = n.get("ref"); m = re.match(r"^\s*(\d{1,2})", str(r or ""))
            if not m: continue
            h = holes.setdefault(m.group(1), {})
            h[n["kind"]] = {"lat": n["lat"], "lng": n["lng"], "osm": n["osm"]}
        rec = {"source": "osm", "attribution": ATTR, "fetched": datetime.date.today().isoformat(), "course": c["id"],
               "holes": holes, "candidates": {"tees": [[n["lat"], n["lng"]] for n in mine if n["kind"] == "tee" and not n.get("ref")],
                                             "baskets": [[n["lat"], n["lng"]] for n in baskets if not n.get("ref")]}}
        json.dump(rec, open(f"{GEO}/{c['id']}.json", "w"), ensure_ascii=False); geo_written += 1
        c["geo_osm"] = {"holes_assigned": len(holes), "baskets": len(baskets)}
    out = arr if isinstance(raw, list) else dict(raw, courses=arr)
    json.dump(out, open(CAT, "w"), indent=1, ensure_ascii=False)
    print(f"catalog: {len(arr)} courses · osm matched {matched} · added {added} · geometry files {geo_written}")


if __name__ == "__main__":
    main()
