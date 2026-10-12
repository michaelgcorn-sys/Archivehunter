"""Find a poster image for every UFO-file video on DVIDS (the military's public media site), so the app can show a
real frame instead of a typed page. Saves data/probe/dvids_thumbs.json: {dvidsVideoId: image_url}."""
import json
import os
import re
import time

import requests

UA = {"User-Agent": "ArchiveHunter/1.0 (research app; github.com/michaelgcorn-sys/Archivehunter)"}
recs = json.load(open("data/ufo_records.json"))
ids = sorted({str(r["dvidsVideoId"]) for r in recs if r.get("dvidsVideoId")})
out, fails = {}, []
for i, vid in enumerate(ids):
    img = None
    for url in (f"https://www.dvidshub.net/video/{vid}", f"https://www.dvidshub.net/video/embed/{vid}"):
        try:
            t = requests.get(url, headers=UA, timeout=25).text
        except Exception as e:
            fails.append(f"{vid}:{type(e).__name__}")
            continue
        m = (re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', t)
             or re.search(r'poster="([^"]+)"', t) or re.search(r'"image"\s*:\s*"(https?:[^"]+\.jpe?g[^"]*)"', t))
        if m:
            img = m.group(1).replace("\\/", "/")
            break
    if img:
        out[vid] = img
    if i < 3:
        print(f"::notice::{vid} -> {img} (status sample)", flush=True)
    time.sleep(0.4)
os.makedirs("data/probe", exist_ok=True)
json.dump(out, open("data/probe/dvids_thumbs.json", "w"), indent=0)
print(f"::notice::DVIDS posters found {len(out)} of {len(ids)}; fails {len(fails)} {fails[:5]}", flush=True)
