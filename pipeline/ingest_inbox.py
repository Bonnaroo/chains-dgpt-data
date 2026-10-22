#!/usr/bin/env python3
"""Ingest hand-collected course files from data/inbox/ into the catalog (see pipeline/SCHEMA.md).

Accepts .json (one record or a list), .jsonl, and .csv (courses.csv / holes.csv pairs). Records must carry a
legal `source` (osm, pdga-license, metrix-api, gov:<agency>, player, owner, manual) or they are skipped and
listed in data/inbox/rejected.log. Matched by id, else by proximity (300 m) / same name within 2 km, else added.
Hand-made fields already in the catalog are kept unless the incoming record is newer (`collected`) and from a
human source (owner/manual/player). Hole geometry goes to data/geo/<courseId>.json.
"""
import csv, glob, json, math, os, re, shutil, datetime

CAT = "data/courses.json"; INBOX = "data/inbox"; GEO = "data/geo"
OK_SOURCES = ("osm", "pdga-license", "metrix-api", "player", "owner", "manual")
HUMAN = ("owner", "manual", "player")


def dist_m(a, b):
    R = 6371000.0
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def norm(s): return re.sub(r"[^a-z0-9]+", " ", re.sub(r"\b(disc golf|dgc|dg|course|park|the)\b", " ", (s or "").lower())).strip()
def slug(s): return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:40]


def read_file(path):
    if path.endswith(".jsonl"):
        return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    if path.endswith(".json"):
        v = json.load(open(path, encoding="utf-8")); return v if isinstance(v, list) else [v]
    if path.endswith(".csv") and not path.endswith("holes.csv"):
        rows = list(csv.DictReader(open(path, encoding="utf-8")))
        for r in rows:
            for k in ("hole_pars", "hole_lengths", "play_order"):
                if r.get(k): r[k] = [int(x) for x in str(r[k]).replace(",", "|").split("|") if x.strip()]
            for k in ("lat", "lng"):
                if r.get(k): r[k] = float(r[k])
            if r.get("holes"): r["holes"] = int(r["holes"])
        holes_path = os.path.join(os.path.dirname(path), "holes.csv")
        if os.path.exists(holes_path):
            byc = {}
            for h in csv.DictReader(open(holes_path, encoding="utf-8")):
                g = byc.setdefault(h["course_id"], {})
                e = {}
                if h.get("tee_lat"): e["tee"] = [float(h["tee_lat"]), float(h["tee_lng"])]
                if h.get("basket_lat"): e["basket"] = [float(h["basket_lat"]), float(h["basket_lng"])]
                if h.get("doglegs"): e["doglegs"] = [[float(a), float(b)] for a, b in (p.split(",") for p in h["doglegs"].split(";") if p.strip())]
                g[str(int(h["hole"]))] = e
            for r in rows:
                if r.get("id") in byc: r["geo"] = byc[r["id"]]
        return rows
    return []


def main():
    raw = json.load(open(CAT)); arr = raw if isinstance(raw, list) else raw.get("courses")
    located = [c for c in arr if c.get("lat") is not None]; by_id = {c["id"]: c for c in arr}
    files = [f for f in glob.glob(f"{INBOX}/**/*", recursive=True) if os.path.isfile(f) and "/done/" not in f and not f.endswith(("rejected.log", ".md"))]
    added = updated = rejected = 0; rej = []
    for f in files:
        for r in read_file(f):
            src = str(r.get("source") or "")
            if not (src in OK_SOURCES or src.startswith("gov:")) or not r.get("name") or r.get("lat") is None or r.get("lng") is None:
                rejected += 1; rej.append(f"{f}: {r.get('name')!r} source={src!r} lat={r.get('lat')!r}"); continue
            st = (r.get("state") or "xx").lower(); cid = r.get("id") or f"{st}-{slug(r['name'])}"
            c = by_id.get(cid)
            if not c:
                best = 400
                for x in located:
                    if abs(x["lat"] - r["lat"]) > 0.02 or abs(x["lng"] - r["lng"]) > 0.03: continue
                    d = dist_m((x["lat"], x["lng"]), (r["lat"], r["lng"]))
                    if d < 300 and d < best or (d < 2000 and norm(x.get("name")) == norm(r["name"]) and d < best): c, best = x, d
            new = c is None
            if new:
                c = {"id": cid, "added": datetime.date.today().isoformat()}; arr.append(c); located.append(c); by_id[cid] = c
            human_newer = src in HUMAN and str(r.get("collected") or "") >= str(c.get("collected") or "")
            for k, v in r.items():
                if k in ("id", "geo", "layouts") or v in (None, "", []): continue
                if new or c.get(k) in (None, "", [], {}) or human_newer: c[k] = v
            c["source_" + src.split(":")[0].replace("-", "_")] = True; c["collected"] = r.get("collected") or c.get("collected")
            if r.get("geo"):
                os.makedirs(GEO, exist_ok=True)
                gp = f"{GEO}/{c['id']}.json"; g = json.load(open(gp)) if os.path.exists(gp) else {"course": c["id"], "holes": {}}
                for hn, e in r["geo"].items():
                    if e.get("tee") and e.get("basket"): g["holes"][str(hn)] = {"tee": {"lat": e["tee"][0], "lng": e["tee"][1]}, "basket": {"lat": e["basket"][0], "lng": e["basket"][1]}, "doglegs": [{"lat": a, "lng": b} for a, b in e.get("doglegs") or []]}
                g["source"] = src; g["updated"] = datetime.date.today().isoformat(); json.dump(g, open(gp, "w"), ensure_ascii=False)
                c["geo_file"] = True
            added += new; updated += (not new)
        os.makedirs(f"{INBOX}/done", exist_ok=True); shutil.move(f, f"{INBOX}/done/{datetime.date.today().isoformat()}-{os.path.basename(f)}")
    if rej: open(f"{INBOX}/rejected.log", "a").write("\n".join(rej) + "\n")
    json.dump(arr if isinstance(raw, list) else dict(raw, courses=arr), open(CAT, "w"), indent=1, ensure_ascii=False)
    print(f"inbox: {len(files)} files · added {added} · updated {updated} · rejected {rejected}")


if __name__ == "__main__":
    main()
