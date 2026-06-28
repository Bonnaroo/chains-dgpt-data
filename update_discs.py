#!/usr/bin/env python3
"""Rebuild data/discs.json from the DiscIt API. Run weekly by GitHub Actions.
Wraps the open DiscIt API (discit-api.fly.dev) into the Chains disc catalog shape."""
import json, urllib.request, datetime, os

API = "https://discit-api.fly.dev/disc"
OUT = os.path.join("data", "discs.json")

def num(x):
    try: return float(x) if "." in str(x) else int(x)
    except: return None

def main():
    req = urllib.request.Request(API, headers={"User-Agent": "ChainsDGPT/1.0"})
    raw = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
    discs = [{
        "brand": d.get("brand"),
        "mold":  d.get("name"),
        "type":  d.get("category"),
        "speed": num(d.get("speed")),
        "glide": num(d.get("glide")),
        "turn":  num(d.get("turn")),
        "fade":  num(d.get("fade")),
        "stability": d.get("stability"),
        "pic":   d.get("pic"),
    } for d in raw]
    discs.sort(key=lambda x: ((x["brand"] or "").lower(), (x["mold"] or "").lower()))
    out = {"_meta": {"source": "DiscIt API (discit-api.fly.dev)",
                     "count": len(discs),
                     "built": datetime.date.today().isoformat(),
                     "fields": "brand, mold, type, speed/glide/turn/fade, stability, pic"},
           "discs": discs}
    os.makedirs("data", exist_ok=True)
    json.dump(out, open(OUT, "w"), indent=1)
    print(f"wrote {OUT}: {len(discs)} discs")

if __name__ == "__main__":
    main()
