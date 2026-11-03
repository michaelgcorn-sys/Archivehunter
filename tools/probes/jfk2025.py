"""What do the 2025 JFK / RFK / MLK release pages on archives.gov look like (for indexing)?"""
import re

import requests

UA = {"User-Agent": "Mozilla/5.0 ArchiveHunter/1.0"}
for u in ["https://www.archives.gov/research/jfk/release-2025", "https://www.archives.gov/research/rfk",
          "https://www.archives.gov/research/mlk", "https://www.archives.gov/research/jfk/release-2025/2025-files"]:
    try:
        r = requests.get(u, headers=UA, timeout=40)
        pdfs = re.findall(r'href="([^"]+\.pdf)"', r.text)
        links = re.findall(r'href="(/research/[^"]+)"', r.text)
        print(f"::notice::{u} -> {r.status_code}, {len(r.text)//1024}KB, {len(pdfs)} PDFs e.g. {pdfs[:3]}, "
              f"sublinks {sorted(set(links))[:12]}", flush=True)
    except Exception as e:
        print(f"::notice::{u} ERROR {e}", flush=True)
