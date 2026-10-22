#!/usr/bin/env python3
"""Every disc golf course OpenStreetMap knows about, nationwide — courses AND their mapped tees/baskets.

Source: OpenStreetMap via the Overpass API. Licence: ODbL (attribution "© OpenStreetMap contributors";
derived databases we publish stay open). One polite query per state (or per country for the rest of the
world), retried across two Overpass mirrors. Output is a SOURCE file; merge_courses.py folds it into the
app catalog with provenance.

  data/sources/osm/courses.json   [{osm:"way/123", name, lat, lng, state, country, holes, website, operator,
                                    fee, tags:{...}, mapped:{tees,baskets}}]
  data/sources/osm/nodes.json     [{osm, kind:"tee"|"basket", lat, lng, ref, course_osm|null}]
  data/sources/osm/meta.json      {fetched, states:{..counts..}}

Run: python3 pipeline/collect_osm_courses.py [US|WORLD|MI,OH,...]   (default US). ~8 minutes for the US.
"""
import json, math, os, sys, time, urllib.parse, urllib.request, datetime

ENDPOINTS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
UA = "Chains/1.0 (open course catalog; github.com/Bonnaroo/chains-dgpt-data; contact via repo)"
OUT = "data/sources/osm"
ATTACH_M = 1500          # a tee/basket this close to a course centre belongs to it
PAUSE = 4                # seconds between queries — be a good citizen

# Rough bounding boxes (south, west, north, east). Oversized on purpose; de-dup by osm id.
STATES = {
 "AL": (30.1,-88.5,35.1,-84.8), "AK": (51.0,-180.0,71.6,-129.9), "AZ": (31.3,-114.9,37.1,-109.0), "AR": (33.0,-94.7,36.6,-89.6),
 "CA": (32.5,-124.5,42.1,-114.1), "CO": (36.9,-109.1,41.1,-102.0), "CT": (40.9,-73.8,42.1,-71.7), "DE": (38.4,-75.8,39.9,-75.0),
 "FL": (24.4,-87.7,31.1,-79.9), "GA": (30.3,-85.7,35.1,-80.8), "HI": (18.8,-160.3,22.3,-154.7), "ID": (41.9,-117.3,49.1,-111.0),
 "IL": (36.9,-91.6,42.6,-87.4), "IN": (37.7,-88.2,41.8,-84.7), "IA": (40.3,-96.7,43.6,-90.1), "KS": (36.9,-102.1,40.1,-94.5),
 "KY": (36.4,-89.6,39.2,-81.9), "LA": (28.9,-94.1,33.1,-88.7), "ME": (42.9,-71.1,47.5,-66.9), "MD": (37.8,-79.5,39.8,-74.9),
 "MA": (41.2,-73.6,42.9,-69.9), "MI": (41.6,-90.5,48.4,-82.3), "MN": (43.4,-97.3,49.4,-89.4), "MS": (30.1,-91.7,35.1,-88.0),
 "MO": (35.9,-95.8,40.7,-89.0), "MT": (44.3,-116.1,49.1,-104.0), "NE": (39.9,-104.1,43.1,-95.2), "NV": (35.0,-120.1,42.1,-113.9),
 "NH": (42.6,-72.6,45.4,-70.6), "NJ": (38.9,-75.6,41.4,-73.8), "NM": (31.3,-109.1,37.1,-102.9), "NY": (40.4,-79.8,45.1,-71.8),
 "NC": (33.8,-84.4,36.7,-75.4), "ND": (45.9,-104.1,49.1,-96.5), "OH": (38.3,-84.9,42.4,-80.4), "OK": (33.5,-103.1,37.1,-94.3),
 "OR": (41.9,-124.7,46.4,-116.4), "PA": (39.6,-80.6,42.4,-74.6), "RI": (41.1,-71.9,42.1,-71.1), "SC": (32.0,-83.4,35.3,-78.5),
 "SD": (42.4,-104.1,46.0,-96.4), "TN": (34.9,-90.4,36.8,-81.6), "TX": (25.7,-106.7,36.6,-93.4), "UT": (36.9,-114.1,42.1,-109.0),
 "VT": (42.6,-73.5,45.1,-71.4), "VA": (36.4,-83.7,39.5,-75.2), "WA": (45.5,-124.9,49.1,-116.9), "WV": (37.1,-82.7,40.7,-77.7),
 "WI": (42.4,-92.9,47.1,-86.7), "WY": (40.9,-111.1,45.1,-104.0), "DC": (38.7,-77.2,39.1,-76.8),
}
WORLD = {"EU": (34.0,-25.0,72.0,45.0), "CA-NA": (41.0,-141.0,70.0,-52.0), "OCE": (-48.0,110.0,-8.0,180.0), "ASIA": (-11.0,45.0,55.0,150.0), "LATAM": (-56.0,-93.0,33.0,-33.0), "AFR": (-35.0,-20.0,37.0,52.0)}


def overpass(box):
    s, w, n, e = box
    q = ('[out:json][timeout:180];(nwr["leisure"="disc_golf_course"](%s,%s,%s,%s);nwr["sport"="disc_golf"](%s,%s,%s,%s);'
         'node["disc_golf"~"^(tee|basket)$"](%s,%s,%s,%s););out tags center 20000;') % ((s, w, n, e) * 3)
    for ep in ENDPOINTS:
        for attempt in range(3):
            try:
                req = urllib.request.Request(ep + "?" + urllib.parse.urlencode({"data": q}), headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=240) as r:
                    return json.load(r).get("elements", [])
            except Exception as ex:
                print("  overpass retry", ep.split("/")[2], attempt, str(ex)[:60], file=sys.stderr); time.sleep(15 * (attempt + 1))
    return None


def dist_m(a, b):
    R = 6371000.0
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def center(e):
    if "lat" in e: return (e["lat"], e["lon"])
    c = e.get("center") or {}; return (c.get("lat"), c.get("lon"))


def holes_of(t):
    for k in ("disc_golf:holes", "holes", "disc_golf:hole_count", "hole_count"):
        v = t.get(k)
        if v and str(v).isdigit(): return int(v)
    return None


# ---- state lookup: Census cartographic boundaries (public domain), cached once in data/sources/us_states.json
FIPS = {"01":"AL","02":"AK","04":"AZ","05":"AR","06":"CA","08":"CO","09":"CT","10":"DE","11":"DC","12":"FL","13":"GA","15":"HI","16":"ID","17":"IL","18":"IN","19":"IA","20":"KS","21":"KY","22":"LA","23":"ME","24":"MD","25":"MA","26":"MI","27":"MN","28":"MS","29":"MO","30":"MT","31":"NE","32":"NV","33":"NH","34":"NJ","35":"NM","36":"NY","37":"NC","38":"ND","39":"OH","40":"OK","41":"OR","42":"PA","44":"RI","45":"SC","46":"SD","47":"TN","48":"TX","49":"UT","50":"VT","51":"VA","53":"WA","54":"WV","55":"WI","56":"WY","72":"PR"}
STATES_URL = "https://eric.clst.org/assets/wiki/uploads/Stuff/gz_2010_us_040_00_20m.json"
_polys = None
def load_states():
    global _polys
    if _polys is not None: return _polys
    path = "data/sources/us_states.json"
    if not os.path.exists(path):
        os.makedirs("data/sources", exist_ok=True)
        try:
            req = urllib.request.Request(STATES_URL, headers={"User-Agent": UA})
            open(path, "wb").write(urllib.request.urlopen(req, timeout=120).read())
        except Exception as ex:
            print("states file unavailable:", ex, file=sys.stderr); _polys = []; return _polys
    g = json.load(open(path)); _polys = []
    for f in g["features"]:
        st = FIPS.get(f["properties"]["STATE"]); geom = f["geometry"]
        rings = geom["coordinates"] if geom["type"] == "Polygon" else [r for poly in geom["coordinates"] for r in poly]
        outer = [rings[0]] if geom["type"] == "Polygon" else [poly[0] for poly in geom["coordinates"]]
        for ring in outer:
            xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
            _polys.append((st, min(xs), min(ys), max(xs), max(ys), ring))
    return _polys
def pip(lng, lat, ring):
    inside = False; n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]; x2, y2 = ring[(i + 1) % n]
        if (y1 > lat) != (y2 > lat):
            x = x1 + (lat - y1) * (x2 - x1) / ((y2 - y1) or 1e-12)
            if x > lng: inside = not inside
    return inside
def state_of(lat, lng):
    for st, x0, y0, x1, y1, ring in load_states():
        if x0 <= lng <= x1 and y0 <= lat <= y1 and pip(lng, lat, ring): return st
    return None


def main():
    arg = (sys.argv[1] if len(sys.argv) > 1 else "US").upper()
    boxes = STATES if arg == "US" else WORLD if arg == "WORLD" else {k: STATES[k] for k in arg.split(",") if k in STATES}
    os.makedirs(OUT, exist_ok=True)
    courses, nodes, meta = {}, {}, {"fetched": datetime.datetime.utcnow().isoformat() + "Z", "regions": {}}
    for region, box in boxes.items():
        els = overpass(box)
        if els is None:
            meta["regions"][region] = "FAILED"; print(region, "FAILED"); time.sleep(PAUSE); continue
        nc = nn = 0
        for e in els:
            t = e.get("tags", {}) or {}
            key = e["type"] + "/" + str(e["id"])
            if t.get("leisure") == "disc_golf_course" or t.get("sport") == "disc_golf":
                la, lo = center(e)
                if la is None: continue
                courses[key] = {"osm": key, "name": t.get("name") or t.get("official_name") or None, "lat": la, "lng": lo,
                                "region": region, "country": "US" if region in STATES else None, "state": region if region in STATES else None,
                                "holes": holes_of(t), "website": t.get("website") or t.get("contact:website"), "operator": t.get("operator"),
                                "fee": t.get("fee"), "access": t.get("access"), "wikidata": t.get("wikidata"),
                                "tags": {k: v for k, v in t.items() if k in ("name", "description", "opening_hours", "phone", "addr:street", "addr:city", "addr:state", "addr:postcode", "surface", "lit", "dog", "wheelchair")}}
                nc += 1
            elif e["type"] == "node" and t.get("disc_golf") in ("tee", "basket"):
                nodes[key] = {"osm": key, "kind": t["disc_golf"], "lat": e["lat"], "lng": e["lon"], "ref": t.get("ref"), "course_osm": None}
                nn += 1
        meta["regions"][region] = {"courses": nc, "nodes": nn}
        print(f"{region}: {nc} courses, {nn} tees/baskets", flush=True)
        time.sleep(PAUSE)
    # true state from Census polygons (query boxes overlap neighbours); drop foreign points on a US run
    cl = list(courses.values())
    if arg != "WORLD":
        for c in cl:
            st = state_of(c["lat"], c["lng"]); c["state"] = st; c["country"] = "US" if st else None
        cl = [c for c in cl if c["state"]]
        courses = {c["osm"]: c for c in cl}
        for nd in list(nodes.values()):
            if not state_of(nd["lat"], nd["lng"]): del nodes[nd["osm"]]
    # attach nodes to nearest course within ATTACH_M
    for nd in nodes.values():
        best, bd = None, ATTACH_M
        for c in cl:
            if abs(c["lat"] - nd["lat"]) > 0.03 or abs(c["lng"] - nd["lng"]) > 0.04: continue
            d = dist_m((c["lat"], c["lng"]), (nd["lat"], nd["lng"]))
            if d < bd: best, bd = c, d
        if best: nd["course_osm"] = best["osm"]
    for c in cl:
        mine = [n for n in nodes.values() if n["course_osm"] == c["osm"]]
        c["mapped"] = {"tees": sum(1 for n in mine if n["kind"] == "tee"), "baskets": sum(1 for n in mine if n["kind"] == "basket")}
    json.dump(sorted(cl, key=lambda c: (c["region"], c["name"] or "")), open(f"{OUT}/courses.json", "w"), indent=1, ensure_ascii=False)
    json.dump(list(nodes.values()), open(f"{OUT}/nodes.json", "w"), ensure_ascii=False)
    meta["totals"] = {"courses": len(cl), "named": sum(1 for c in cl if c["name"]), "nodes": len(nodes), "courses_with_geometry": sum(1 for c in cl if c["mapped"]["baskets"] >= 9)}
    json.dump(meta, open(f"{OUT}/meta.json", "w"), indent=1)
    print("TOTAL", meta["totals"])


if __name__ == "__main__":
    main()
