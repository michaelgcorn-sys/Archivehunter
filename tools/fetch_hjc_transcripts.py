"""Fetch the House Judiciary Committee's 1974 transcript comparison (public domain, govinfo) and save its text."""
import gzip
import io
import json
import os

import requests
from pypdf import PdfReader

URLS = ["https://www.govinfo.gov/content/pkg/CHRG-93hhrg36316O/pdf/CHRG-93hhrg36316O.pdf",
        "https://watergate.info/judiciary/REC.PDF"]
UA = {"User-Agent": "Mozilla/5.0 (research app ArchiveHunter; github.com/michaelgcorn-sys/Archivehunter)"}
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "hjc1974_pages.json.gz")

for url in URLS:
    try:
        r = requests.get(url, headers=UA, timeout=180)
    except requests.RequestException as e:
        print(f"::warning::{url} {type(e).__name__}")
        continue
    print(f"::notice::{url} -> {r.status_code} {r.headers.get('content-type','')} {len(r.content)} bytes")
    if r.status_code == 200 and r.content[:4] == b"%PDF":
        pages = [(p.extract_text() or "") for p in PdfReader(io.BytesIO(r.content)).pages]
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with gzip.open(OUT, "wt", encoding="utf-8") as f:
            json.dump({"source": url, "pages": pages}, f, ensure_ascii=False)
        print(f"::notice::wrote {len(pages)} pages, {sum(len(p) for p in pages)} chars")
        break
