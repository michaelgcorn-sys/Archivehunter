"""Fetch the 1974 'Submission of Recorded Presidential Conversations' (GPO, public domain) page text from HathiTrust.

Usage: python tools/fetch_wh_transcripts.py [first_seq] [last_seq]
Writes data/wh1974_pages.json.gz  ({seq: text}). Polite: one page at a time with a pause.
"""
import gzip
import html
import json
import os
import re
import sys
import time

import requests

ID = "pur1.32754081232310"
UA = {"User-Agent": "Mozilla/5.0 (research app ArchiveHunter; github.com/michaelgcorn-sys/Archivehunter)"}
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "wh1974_pages.json.gz")


def page_text(seq):
    for url in (f"https://babel.hathitrust.org/cgi/ssd?id={ID};seq={seq}",
                f"https://babel.hathitrust.org/cgi/pt?id={ID}&seq={seq}&view=plaintext"):
        for attempt in range(3):
            try:
                r = requests.get(url, headers=UA, timeout=60)
            except requests.RequestException:
                time.sleep(5)
                continue
            if r.status_code == 200:
                m = (re.search(r'(?is)<div[^>]+id="mdpText"[^>]*>(.*?)</div>', r.text)
                     or re.search(r'(?is)<p[^>]+class="Text"[^>]*>(.*?)</p>', r.text)
                     or re.search(r'(?is)<pre[^>]*>(.*?)</pre>', r.text))
                if m:
                    return html.unescape(re.sub(r"<br\s*/?>", "\n", re.sub(r"(?s)<(?!br)[^>]+>", "", m.group(1)))).strip(), url, r.status_code
                return None, url, f"200 but no text block ({len(r.text)} chars): " + re.sub(r"\s+", " ", r.text[:200])
            if r.status_code in (403, 429):
                time.sleep(20 * (attempt + 1))
                continue
            break
    return None, url, r.status_code if 'r' in dir() else "error"


def main():
    first = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    last = int(sys.argv[2]) if len(sys.argv) > 2 else 1308
    pages = {}
    if os.path.exists(OUT):
        with gzip.open(OUT, "rt") as f:
            pages = json.load(f)
    fails = 0
    for seq in range(first, last + 1):
        if str(seq) in pages:
            continue
        text, url, status = page_text(seq)
        if text is None:
            fails += 1
            print(f"::warning::seq {seq} failed: {status} ({url})", flush=True)
            if fails >= 15 and not pages:
                print("::error::giving up: nothing readable", flush=True)
                break
        else:
            pages[str(seq)] = text
        if seq % 50 == 0 or seq == first:
            print(f"::notice::seq {seq}: {len(pages)} pages so far; sample: {(text or '')[:160]!r}", flush=True)
        time.sleep(1.0)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with gzip.open(OUT, "wt", encoding="utf-8") as f:
        json.dump(pages, f, ensure_ascii=False)
    print(f"::notice::wrote {len(pages)} pages", flush=True)


if __name__ == "__main__":
    main()
