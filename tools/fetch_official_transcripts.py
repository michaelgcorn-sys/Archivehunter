"""NOTE (Oct 2026): the Nixon Library listing pages embed each transcript as a Drupal media item that
currently renders empty, even in a real browser, so this finds nothing usable yet. Kept for when they fix it.

Collect the Nixon Library's official (public-domain) tape transcripts for the app.

Runs in GitHub Actions. Reads the two Nixon Library transcript listings, finds each conversation and
any transcript file linked from the listing or from the conversation's own page, extracts the text and
writes data/nixon_transcripts.json.gz keyed by conversation number (e.g. "472-004").
"""
import gzip
import io
import json
import os
import re
import time

import requests
from pypdf import PdfReader

BASE = "https://www.nixonlibrary.gov"
UA = {"User-Agent": "ArchiveHunter-index-builder/1.0 (research app; github.com/michaelgcorn-sys/Archivehunter)"}
LISTINGS = {"Watergate Special Prosecution Force": BASE + "/watergate-special-prosecution-force-transcripts",
            "Watergate trial tapes": BASE + "/watergate-trial-tapes"}
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "nixon_transcripts.json.gz")
PAUSE = 0.6
CONV = re.compile(r"\b(\d{3})-(\d{3})\b")


def get(url):
    for i in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=60)
            if r.status_code == 200:
                return r
            if r.status_code == 404:
                return None
        except requests.RequestException:
            pass
        time.sleep(3 * (i + 1))
    return None


def absu(u):
    return u if u.startswith("http") else BASE + (u if u.startswith("/") else "/" + u)


def text_of(data, ctype):
    if data[:4] == b"%PDF" or "pdf" in ctype:
        try:
            return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
        except Exception:
            return ""
    try:
        html = data.decode("utf-8", "ignore")
    except Exception:
        return ""
    html = re.sub(r"(?is)<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", html)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def main():
    found = {}                       # conv -> {"set":…, "links": set()}
    for set_name, url in LISTINGS.items():
        r = get(url)
        time.sleep(PAUSE)
        if r is None:
            print("could not read", url)
            continue
        page = r.text
        rows = re.split(r"(?i)<tr\b", page)
        for row in rows:
            convs = {f"{a}-{b}" for a, b in CONV.findall(re.sub(r"<[^>]+>", " ", row))}
            links = [absu(h) for h in re.findall(r'href="([^"#]+)"', row)]
            for c in convs:
                e = found.setdefault(c, {"set": set_name, "links": set()})
                e["links"].update(l for l in links if re.search(r"\.(pdf|txt)$", l, re.I))
        print(set_name, "conversations so far:", len(found), flush=True)

    out = {}
    for conv, e in sorted(found.items()):
        tape = conv.split("-")[0]
        cpage = f"{BASE}/white-house-tapes/{tape}/conversation-{conv}"
        r = get(cpage)
        time.sleep(PAUSE)
        if r is not None:
            e["links"].update(absu(h) for h in re.findall(r'href="([^"#]+)"', r.text)
                              if re.search(r"transcript", h, re.I) and not h.endswith("-log.pdf"))
        best = ""
        used = None
        for link in sorted(e["links"]):
            rr = get(link)
            time.sleep(PAUSE)
            if rr is None:
                continue
            t = text_of(rr.content, rr.headers.get("content-type", ""))
            if len(t) > len(best):
                best, used = t, link
        print(conv, len(best), used, flush=True)
        if len(best) > 400:
            out[conv] = {"set": e["set"], "url": used, "page": cpage, "text": best}

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    meta = {"built": time.strftime("%Y-%m-%d"), "conversations_listed": len(found), "with_text": len(out)}
    with gzip.open(OUT, "wt", encoding="utf-8") as f:
        json.dump({"meta": meta, "transcripts": out}, f, ensure_ascii=False)
    print("wrote", meta, flush=True)


if __name__ == "__main__":
    main()
