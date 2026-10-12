"""Pick the most watchable poster frame for each UFO video: tries several DVIDS frames, scores brightness and
contrast, drops near-black ones. Writes data/probe/dvids_best.json and a contact sheet to eyeball the picks."""
import io
import json
import os
import re

import requests
from PIL import Image, ImageStat

UA = {"User-Agent": "ArchiveHunter/1.0 (research app; github.com/michaelgcorn-sys/Archivehunter)"}
src = json.load(open("data/dvids_thumbs.json"))
best, tiles = {}, []
for vid, url in src.items():
    picks = []
    for n in range(1, 9):
        u = re.sub(r"\.\d{7}/", f".{n:07d}/", url)
        try:
            r = requests.get(u, headers=UA, timeout=20)
            if r.status_code != 200 or len(r.content) < 2000:
                continue
            im = Image.open(io.BytesIO(r.content)).convert("L").resize((160, 90))
            st = ImageStat.Stat(im)
            mean, sd = st.mean[0], st.stddev[0]
            picks.append((sd + 0.3 * min(mean, 120), u, mean, sd, r.content))
        except Exception:
            continue
    if not picks:
        continue
    score, u, mean, sd, raw = max(picks)
    if mean < 18 or sd < 10:          # basically a black or flat frame
        continue
    best[vid] = u
    tiles.append((vid, raw))
os.makedirs("data/probe", exist_ok=True)
json.dump(best, open("data/probe/dvids_best.json", "w"), indent=0)
W, H, cols = 240, 135, 6
sheet = Image.new("RGB", (W * cols, H * ((len(tiles) + cols - 1) // cols) or H), "black")
for k, (vid, raw) in enumerate(tiles):
    im = Image.open(io.BytesIO(raw)).convert("RGB").resize((W, H))
    sheet.paste(im, ((k % cols) * W, (k // cols) * H))
sheet.save("data/probe/dvids_sheet.jpg", quality=70)
print(f"::notice::usable posters {len(best)} of {len(src)}", flush=True)
