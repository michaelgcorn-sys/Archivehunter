"""Index the 2025 JFK, RFK and MLK assassination-records releases posted on archives.gov (ordered declassified by
Executive Order 14176). Writes data/assassination_2025.json: [{set, title, url, date}]."""
import html
import json
import os
import re
import urllib.parse

import requests

UA = {"User-Agent": "Mozilla/5.0 ArchiveHunter/1.0"}
PAGES = {"JFK": "https://www.archives.gov/research/jfk/release-2025",
         "RFK": "https://www.archives.gov/research/rfk",
         "MLK": "https://www.archives.gov/research/mlk"}
out, seen = [], set()
for name, page in PAGES.items():
    t = requests.get(page, headers=UA, timeout=60).text
    n0 = len(out)
    for row in re.split(r"(?i)<tr\b", t):
        m = re.search(r'href="([^"]+\.pdf)"', row)
        if not m:
            continue
        url = urllib.parse.urljoin(page, m.group(1)).replace(" ", "%20")
        if url in seen:
            continue
        seen.add(url)
        cells = [html.unescape(re.sub(r"<[^>]+>", " ", c)).strip() for c in re.split(r"(?i)</t[dh]>", row)]
        cells = [re.sub(r"\s+", " ", c) for c in cells if c.strip()]
        fname = urllib.parse.unquote(url.rsplit("/", 1)[1])[:-4]
        words = re.sub(r"^\d+_", "", fname).replace("_", " ")
        dm = re.search(r"/releases/(\d{4})/(\d\d)(\d\d)/", url)
        out.append({"set": name, "title": " · ".join(cells[:4])[:300] or words, "file": words,
                    "url": url, "date": f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}" if dm else ""})
    print(f"::notice::{name}: {len(out) - n0} documents; e.g. {[x['title'][:80] for x in out[n0:n0 + 3]]}", flush=True)
p = os.path.join(os.path.dirname(__file__), "..", "data", "assassination_2025.json")
json.dump(out, open(p, "w"), ensure_ascii=False, separators=(",", ":"))
