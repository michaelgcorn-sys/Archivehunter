"""Index the CIA reading room's UFO documents (via its Internet Archive mirror). Writes data/cia_ufo.json."""
import json
import os
import re
import time

import requests

UA = {"User-Agent": "ArchiveHunter/1.0 (research app; github.com/michaelgcorn-sys/Archivehunter)"}
API = "https://archive.org/services/search/v1/scrape"
Q = ('collection:ciareadingroom AND (UFO OR UFOS OR "flying saucer" OR "flying saucers" OR "flying disc" OR '
     '"unidentified flying" OR "unidentified aerial" OR "unidentified anomalous" OR UAP)')
rows, cursor = [], None
while True:
    params = {"q": Q, "fields": "identifier,title,date,description,imagecount", "count": 5000}
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
    if not cursor:
        break


def one(v):
    return (v[0] if isinstance(v, list) and v else v) or ""


UFO_RX = re.compile(r"(?i)\bUFOs?\b|flying saucer|flying dis[ck]|unidentified (?:flying|aerial|anomalous)|\bUAPs?\b|saucer")
out = []
for d in rows:
    t = re.sub(r"^CIA Reading Room\s+[\w-]+:\s*", "", one(d.get("title"))).strip()
    desc = re.sub(r"\s+", " ", one(d.get("description")))[:400]
    if not UFO_RX.search(t + " " + desc):        # skip files that only mention UFOs somewhere in the scanned text
        continue
    m = re.search(r"(19|20)\d\d", one(d.get("date")) or t)
    out.append({"id": d["identifier"], "title": t or d["identifier"], "year": int(m.group()) if m else None,
                "desc": desc, "pages": d.get("imagecount")})
out.sort(key=lambda r: (r["year"] or 9999, r["title"]))
p = os.path.join(os.path.dirname(__file__), "..", "data", "cia_ufo.json")
json.dump(out, open(p, "w"), ensure_ascii=False, separators=(",", ":"))
print(f"::notice::CIA UFO documents indexed: {len(out)} of {len(rows)} hits; sample: {[r['title'][:60] for r in out[:4]]}", flush=True)
