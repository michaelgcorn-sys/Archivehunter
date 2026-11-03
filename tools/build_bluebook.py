"""Index the Air Force's Project Blue Book UFO case files posted on the Internet Archive (~10,800 files).
Runs in GitHub Actions. Writes data/bluebook.json.gz: [{id, title, year, month, place, collection}]."""
import gzip
import json
import os
import re
import time

import requests

UA = {"User-Agent": "ArchiveHunter/1.0 (research app; github.com/michaelgcorn-sys/Archivehunter)"}
API = "https://archive.org/services/search/v1/scrape"
Q = '"project blue book" AND mediatype:texts'
rows, cursor = [], None
while True:
    params = {"q": Q, "fields": "identifier,title,date,collection,imagecount", "count": 10000}
    if cursor:
        params["cursor"] = cursor
    for attempt in range(5):
        try:
            j = requests.get(API, params=params, headers=UA, timeout=90).json()
            break
        except Exception as e:
            print("retry", e, flush=True)
            time.sleep(10)
    rows += j.get("items", [])
    cursor = j.get("cursor")
    print(len(rows), "of", j.get("total"), flush=True)
    if not cursor:
        break

CASE = re.compile(r"^\s*((?:19)?\d\d)[\s_-]+(\d\d|xx|XX)[\s_-]+(?:(\d{5,9})[\s_-]+)?(.+)$")
out, colls, unmatched = [], {}, []
for d in rows:
    t = d.get("title") or ""
    if isinstance(t, list):
        t = t[0]
    c = d.get("collection") or []
    c = [c] if isinstance(c, str) else c
    for x in c:
        colls[x] = colls.get(x, 0) + 1
    m = CASE.match(t)
    if not m:
        if len(unmatched) < 12:
            unmatched.append(t)
        continue                                   # keep only actual case files ("1966 08 8725718 Place")
    y = m.group(1)
    y = int(y) if len(y) == 4 else 1900 + int(y)
    mo = m.group(2)
    place = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", m.group(4)).replace("-", " ").replace("_", " ")
    place = re.sub(r"\s+\d+\s*$", "", place).strip()   # "NorthSacramento" -> "North Sacramento"
    out.append({"id": d["identifier"], "title": t.strip(), "year": y, "month": None if mo.lower() == "xx" else int(mo),
                "place": place, "pages": d.get("imagecount")})
out.sort(key=lambda r: (r["year"], r["month"] or 0))
print("::notice::Blue Book case files indexed:", len(out), "of", len(rows), "matching items", flush=True)
print("::notice::top collections:", sorted(colls.items(), key=lambda kv: -kv[1])[:6], flush=True)
print("::notice::not case-file titles, e.g.:", unmatched, flush=True)
print("::notice::years:", out[0]["year"] if out else None, "-", out[-1]["year"] if out else None, "sample:", out[:2], flush=True)
p = os.path.join(os.path.dirname(__file__), "..", "data", "bluebook.json.gz")
with gzip.open(p, "wt") as f:
    json.dump(out, f, separators=(",", ":"))
