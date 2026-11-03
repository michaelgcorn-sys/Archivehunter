"""Index the National Archives' UAP Records Collection (Record Group 615), filled by agencies under the 2024 UAP
disclosure law. Writes data/nara_uap.json: [{naId, title, year, url, pdf, image, files, snippet}]."""
import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import sources as S  # noqa: E402

H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Content-Type": "application/json"}
U = "https://catalog.archives.gov/proxy/v3/records/search"
out, page = [], 1
while True:
    for attempt in range(4):
        try:
            j = requests.get(U, params={"recordGroupNumber": "615", "limit": 100, "page": page}, headers=H, timeout=60).json()
            break
        except Exception as e:
            print("retry", e, flush=True)
            time.sleep(8)
    hits = j.get("body", {}).get("hits", {}).get("hits") or []
    for h in hits:
        rec = (h.get("_source") or {}).get("record") or {}
        na = rec.get("naId")
        if not na:
            continue
        dates = rec.get("productionDates") or rec.get("inclusiveDates") or []
        year = str(dates[0].get("year") or "") if isinstance(dates, list) and dates and isinstance(dates[0], dict) else ""
        files = [d.get("objectUrl") for d in rec.get("digitalObjects") or [] if d.get("objectUrl")]
        pdf = next((u for u in files if u.lower().split("?")[0].endswith(".pdf")), None)
        out.append({"naId": na, "title": S.clean(str(rec.get("title", "")))[:200] or f"Record {na}", "year": year,
                    "url": f"https://catalog.archives.gov/id/{na}", "pdf": pdf, "files": len(files),
                    "image": S._nara_image(rec.get("digitalObjects") or []),
                    "snippet": S.clean(str(rec.get("scopeAndContentNote", "")))[:300]})
    print(page, len(out), flush=True)
    if len(hits) < 100 or page > 30:
        break
    page += 1
    time.sleep(1)
online = sum(1 for r in out if r["files"])
print(f"::notice::RG 615 records indexed: {len(out)} ({online} with files online, "
      f"{sum(1 for r in out if r['image'])} with a picture); e.g. {[r['title'][:60] for r in out[:3]]}", flush=True)
p = os.path.join(os.path.dirname(__file__), "..", "data", "nara_uap.json")
json.dump(out, open(p, "w"), ensure_ascii=False, separators=(",", ":"))
