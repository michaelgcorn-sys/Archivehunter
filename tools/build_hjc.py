"""Turn the House Judiciary Committee 1974 comparison (data/hjc1974_pages.json.gz) into per-conversation
transcript excerpts keyed by tape conversation number -> data/hjc1974.json"""
import gzip
import json
import os
import re

D = os.path.join(os.path.dirname(__file__), "..", "data")
SECTIONS = [  # (first page, last page, conversation, label)
    (8, 13, "779-002", "September 15, 1972 · Oval Office · Nixon, Haldeman, Dean"),
    (14, 17, "865-014", "February 28, 1973 · Oval Office · Nixon, Dean"),
    (18, 23, "878-014", "March 13, 1973 · Oval Office · Nixon, Dean, Haldeman"),
    (24, 37, "886-008", "March 21, 1973 (morning) · Oval Office · Nixon, Dean, Haldeman"),
    (38, 45, "421-018", "March 21, 1973 (evening) · EOB · Nixon, Dean, Ehrlichman, Haldeman"),
    (46, 57, "422-033", "March 22, 1973 · EOB · Nixon, Dean, Ehrlichman, Haldeman, Mitchell"),
    (58, 61, "897-004", "April 16, 1973 (morning) · Oval Office · Nixon, Dean"),
    (62, 70, "427-010", "April 16, 1973 (afternoon) · EOB · Nixon, Dean"),
]


def sp(word):                      # tolerate the scan's stray spaces inside words
    return r"\s*".join(re.escape(c) for c in word)


HJC = re.compile(sp("HOUSE") + r"\s*" + sp("JUDICIARY") + r"\s*" + sp("COMMITTEE") + r"\s*" + sp("TRANSCRIPT") + r"\s*,?\s*(pp?\.\s*[\d\s,\-–]+)", re.I)
WH = re.compile(sp("WHITE") + r"\s*" + sp("HOUSE") + r"\s*" + sp("TRANSCRIPT") + r"\s*,?\s*(pp?\.\s*[\d\s,\-–]+)", re.I)
NAMES = {"President": "President", "Haldeman": "Haldeman", "Dean": "Dean", "Ehrlichman": "Ehrlichman",
         "Mitchell": "Mitchell", "Kleindienst": "Kleindienst", "Petersen": "Petersen"}


def clean(t):
    for n in NAMES:
        t = re.sub(r"(?m)^\s*" + sp(n) + r"\s*[.,]", n + ".", t)          # speaker labels at line start
    t = re.sub(r"(?m)^\s*Eiirlichman", "Ehrlichman", t)
    t = re.sub(r"(?m)^\s*Haldema\s*x", "Haldeman", t)
    t = re.sub(r"(?m)^\s*\d+\s+.*?(Hous|Whi)e .*$", "", t) if False else t
    t = re.sub(r"(?m)^\s*(SEPTEMBER|FEBRUARY|MARCH|APRIL)[\s\dA-Z,.:]*$", "", t)   # running page headers
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n(?![A-Z][a-z]+\.\s|\[|[PHDEM] )", " ", t)            # rejoin wrapped lines; keep speaker turns
    return re.sub(r"\s{2,}", " ", t).replace(" President.", "\nPresident.").strip()


def blocks(text):
    """Split a page into ('hjc'|'wh', page_ref, text) blocks in reading order."""
    marks = sorted([(m.start(), m.end(), "hjc", m.group(1)) for m in HJC.finditer(text)] +
                   [(m.start(), m.end(), "wh", m.group(1)) for m in WH.finditer(text)])
    out = []
    for i, (a, b, kind, ref) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        out.append((kind, re.sub(r"\s+", "", ref), text[b:end]))
    return out


def main():
    with gzip.open(os.path.join(D, "hjc1974_pages.json.gz"), "rt") as f:
        src = json.load(f)
    pages = src["pages"]
    result = {}
    for first, last, conv, label in SECTIONS:
        hjc, wh = [], []
        for p in range(first, last + 1):
            for kind, ref, txt in blocks(pages[p]):
                txt = re.split(r"\n\s*\d\s+The\s+bra", txt)[0]            # drop footnotes
                (hjc if kind == "hjc" else wh).append({"ref": ref, "text": clean(txt), "pdf_page": p + 1})
        result[conv] = {"label": label, "source": "House Judiciary Committee, “Comparison of White House and "
                        "Judiciary Committee Transcripts of Eight Recorded Presidential Conversations” (1974)",
                        "url": src["source"], "committee": hjc, "white_house": wh}
        print(conv, len(hjc), "committee passages,", len(wh), "White House passages")
    with open(os.path.join(D, "hjc1974.json"), "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=0)


if __name__ == "__main__":
    main()
