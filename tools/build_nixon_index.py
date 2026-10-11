"""Build a word-searchable index of the Nixon White House Tape Subject Logs.

Runs in GitHub Actions (not in the app): visits each tape page on nixonlibrary.gov, finds that tape's
subject-log PDF, reads its text (character recognition only if a PDF has no text layer), and writes
data/nixon_logs.json.gz for the app to search.

Polite by design: one request at a time with a pause between them, and a clear User-Agent.
"""
import concurrent.futures as cf
import gzip
import io
import json
import os
import re
import sys
import time

import requests
from pypdf import PdfReader

BASE = "https://www.nixonlibrary.gov"
UA = {"User-Agent": "ArchiveHunter-index-builder/1.0 (research app; github.com/michaelgcorn-sys/Archivehunter)"}
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "nixon_logs.json.gz")
PAUSE = 0.6

GROUPS = [(1, 46, "White House Telephone"), (47, 129, "Cabinet Room"), (130, 169, "Camp David Study Table"),
          (170, 187, "Camp David Study Desk"), (188, 244, "Camp David Hard Wire"),
          (245, 448, "Executive Office Building"), (449, 950, "Oval Office")]


def group_of(n):
    return next((g for a, b, g in GROUPS if a <= n <= b), "")


def get(url, tries=3, **kw):
    for i in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=60, **kw)
            if r.status_code == 200:
                return r
            if r.status_code == 404:
                return None
        except requests.RequestException:
            pass
        time.sleep(3 * (i + 1))
    return None


def pdf_text(data):
    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((p.extract_text() or "") for p in reader.pages), len(reader.pages)
    except Exception:
        return "", 0


def ocr_pdf(data):
    """Character recognition for scanned logs (only used when the PDF has no text layer)."""
    try:
        import pypdfium2 as pdfium
        import pytesseract
    except ImportError:
        return ""
    out = []
    doc = pdfium.PdfDocument(data)
    for i in range(len(doc)):
        img = doc[i].render(scale=2.2).to_pil().convert("L")
        out.append(pytesseract.image_to_string(img))
    return "\n".join(out)


def tape_page(n):
    tape = f"{n:03d}"
    url = f"{BASE}/white-house-tapes/{tape}"
    r = get(url)
    time.sleep(PAUSE)
    if r is None:
        return None
    pdfs = re.findall(r'href="([^"]+\.pdf)"', r.text, re.I)
    pdfs = [p if p.startswith("http") else BASE + p for p in pdfs]
    log = next((p for p in pdfs if "log" in p.lower()), pdfs[0] if pdfs else None)
    convs = sorted(set(re.findall(rf"/white-house-tapes/{tape}/conversation-({tape}-\d+)", r.text)))
    return {"tape": tape, "group": group_of(n), "page": url, "pdf": log, "convs": convs}


def main():
    first, last = 1, 950
    if len(sys.argv) == 3:                                   # e.g. a quick test run: 838 840
        first, last = int(sys.argv[1]), int(sys.argv[2])
    tapes = []
    for n in range(first, last + 1):
        t = tape_page(n)
        if t:
            tapes.append(t)
        if n % 50 == 0:
            print(f"pages: through tape {n}, {len(tapes)} found", flush=True)

    need_ocr = []
    for t in tapes:
        t["text"], t["pages"] = "", 0
        if not t["pdf"]:
            continue
        r = get(t["pdf"])
        time.sleep(PAUSE)
        if r is None:
            continue
        text, pages = pdf_text(r.content)
        t["pages"] = pages
        letters = sum(c.isalpha() for c in text)
        if pages and letters / pages < 200:                  # little or no text layer: scan
            need_ocr.append((t, r.content))
        else:
            t["text"] = text
    print(f"logs read: {sum(1 for t in tapes if t['text'])}, scanned needing OCR: {len(need_ocr)}", flush=True)

    with cf.ProcessPoolExecutor(max_workers=os.cpu_count() or 2) as ex:
        for (t, _), text in zip(need_ocr, ex.map(ocr_pdf, [d for _, d in need_ocr])):
            t["text"], t["ocr"] = text, True

    for t in tapes:
        t["text"] = re.sub(r"[ \t]+", " ", re.sub(r"\n{3,}", "\n\n", t["text"])).strip()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    meta = {"built": time.strftime("%Y-%m-%d"), "tapes": len(tapes),
            "with_text": sum(1 for t in tapes if t["text"]), "source": BASE + "/white-house-tapes"}
    with gzip.open(OUT, "wt", encoding="utf-8") as f:
        json.dump({"meta": meta, "tapes": tapes}, f, ensure_ascii=False)
    print("wrote", OUT, meta, f"{os.path.getsize(OUT) / 1e6:.1f} MB", flush=True)


if __name__ == "__main__":
    main()
