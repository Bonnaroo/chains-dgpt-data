#!/usr/bin/env python3
"""Open course geometry from OpenStreetMap (ODbL, no login, usable anywhere).

Pulls every disc-golf tee / basket node (and course outlines) for the configured
bounding boxes via the Overpass API, attaches each node to the nearest course in
data/courses.json (within ATTACH_M metres), and writes:

  data/geo/osm/<courseId>.json   { source:"osm", fetched, course, holes:{"<n>":{tee,basket}},
                                   candidates:{tees:[...], baskets:[...]} }
  data/geo/osm/index.json        { courseId: {tees, baskets, assigned} }

Nodes that carry `ref=<hole number>` are assigned to that hole; the rest are kept as
candidates so a player can assign them in the app ("this tee is hole 3") or simply
re-mark with GPS. Attribution required wherever this data is shown: "© OpenStreetMap
contributors". Runs weekly from .github/workflows/collect-osm-geo.yml."""
import json, math, os, sys, time, urllib.parse, urllib.request, datetime

BOXES = [  # (south, west, north, east) — Michigan in four chunks so Overpass never times out
    (41.69, -87.0, 43.3, -84.0), (41.69, -84.0, 43.3, -82.3),
    (43.3, -87.0, 45.1, -82.3), (45.1, -90.5, 48.3, -82.3),
]
ENDPOINTS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
ATTACH_M = 1500
UA = "ChainsDGPT/1.0 (course mapping; github.com/Bonnaroo/chains-dgpt-data)"

def overpass(box):
    s, w, n, e = box
    q = ('[out:json][timeout:120];(node["disc_golf"](%s,%s,%s,%s);nwr["leisure"="disc_golf_course"](%s,%s,%s,%s);'
         'nwr["sport"="disc_golf"](%s,%s,%s,%s););out tags center 5000;') % ((s, w, n, e) * 3)
    for ep in ENDPOINTS:
        for attempt in range(3):
            try:
                req = urllib.request.Request(ep + "?" + urllib.parse.urlencode({"data": q}), headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=180) as r:
                    return json.load(r).get("elements", [])
            except Exception as ex:  # 502/504 under load are normal — back off and retry
                print("  overpass retry", ep, attempt, ex, file=sys.stderr); time.sleep(10 * (attempt + 1))
    return []

def dist_m(a, b):
    R = 6371000.0
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))

def main():
    cat = json.load(open("data/courses.json"))
    courses = cat if isinstance(cat, list) else cat.get("courses") or []
    located = [c for c in courses if c.get("lat") is not None and c.get("lng") is not None]
    els = []
    for b in BOXES:
        got = overpass(b); print("box", b, "->", len(got), "elements"); els += got; time.sleep(3)
    # OSM course outlines give us names/centres for courses our catalog doesn't locate yet
    osm_courses = [e for e in els if (e.get("tags", {}).get("leisure") == "disc_golf_course" or e.get("tags", {}).get("sport") == "disc_golf")]
    nodes = [e for e in els if e.get("type") == "node" and e.get("tags", {}).get("disc_golf") in ("tee", "basket")]
    print(len(osm_courses), "osm courses,", len(nodes), "tee/basket nodes")
    def center(e): return (e["lat"], e["lon"]) if "lat" in e else ((e.get("center") or {}).get("lat"), (e.get("center") or {}).get("lon"))
    out = {}
    for nd in nodes:
        p = (nd["lat"], nd["lon"])
        best, bd = None, ATTACH_M
        for c in located:
            d = dist_m(p, (c["lat"], c["lng"]))
            if d < bd: best, bd = c, d
        if not best:
            # fall back to a named OSM course outline → synthetic id so nothing is lost
            for oc in osm_courses:
                cc = center(oc)
                if cc[0] is None: continue
                d = dist_m(p, cc)
                if d < bd and oc.get("tags", {}).get("name"):
                    best, bd = {"id": "osm-" + str(oc["id"]), "name": oc["tags"]["name"], "lat": cc[0], "lng": cc[1], "_osm": True}, d
        if not best: continue
        rec = out.setdefault(best["id"], {"source": "osm", "attribution": "© OpenStreetMap contributors (ODbL)", "fetched": datetime.date.today().isoformat(),
                                          "course": {"id": best["id"], "name": best.get("name"), "lat": best.get("lat"), "lng": best.get("lng")}, "holes": {}, "candidates": {"tees": [], "baskets": []}})
        kind = nd["tags"]["disc_golf"]
        ref = nd["tags"].get("ref")
        pt = {"lat": nd["lat"], "lng": nd["lon"], "osm": nd["id"], "by": "osm", "at": 0}
        if ref and str(ref).isdigit():
            h = str(int(ref) - 1)
            rec["holes"].setdefault(h, {})[kind] = pt
        else:
            rec["candidates"]["tees" if kind == "tee" else "baskets"].append(pt)
    os.makedirs("data/geo/osm", exist_ok=True)
    index = {}
    for cid, rec in out.items():
        with open("data/geo/osm/%s.json" % cid, "w") as f: json.dump(rec, f, indent=1)
        index[cid] = {"name": rec["course"]["name"], "tees": len(rec["candidates"]["tees"]) + sum(1 for h in rec["holes"].values() if "tee" in h),
                      "baskets": len(rec["candidates"]["baskets"]) + sum(1 for h in rec["holes"].values() if "basket" in h), "assigned": len(rec["holes"])}
    with open("data/geo/osm/index.json", "w") as f: json.dump({"fetched": datetime.date.today().isoformat(), "courses": index}, f, indent=1)
    print("wrote", len(out), "courses")

if __name__ == "__main__":
    main()
