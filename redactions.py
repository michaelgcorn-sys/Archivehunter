"""
Before / After: the same government document, first released with black boxes, later released with them removed.

Each case pairs an earlier National Archives release of a JFK-collection record with its March 2025 re-release.
The old-version links come from the National Security Archive's comparison of the 2025 release
(nsarchive.gwu.edu/briefing-book/2025-03-19/cia-covert-ops-kennedy-assassination-records-lift-veil-secrecy).
find_reveal() downloads both PDFs and picks the page where the most black ink disappeared.
"""

import io

from sources import _fetch_bytes

MODULE_VERSION = 65   # keep in step with APP_CODE_VERSION in app.py

NARA_2025 = "https://www.archives.gov/files/research/jfk/releases/2025/0318/{rec}.{ext}"
NSA_POST = "https://nsarchive.gwu.edu/briefing-book/2025-03-19/cia-covert-ops-kennedy-assassination-records-lift-veil-secrecy"

CASES = [
    {"key": "jewels", "short": "The “Family Jewels”", "record": "104-10303-10007",
     "title": "CIA “Family Jewels” memo: “Special Activities”",
     "when": "Written June 1, 1973 · blacked out in the 2023 release · reopened March 2025",
     "old": "https://www.archives.gov/files/research/jfk/releases/2023/104-10303-10007.pdf",
     "what": "In 1973 the CIA's director ordered staff to list every past activity that might be illegal or "
             "embarrassing. The answers became known as the “Family Jewels.” This memo is one of them.",
     "why": "The CIA withheld passages for decades to protect sources, methods and relations with foreign "
            "governments. The National Security Archive says the 2025 version restores passages about a break-in "
            "at the French consulate and contacts with the Vatican."},
    {"key": "trujillo", "short": "The Trujillo Report", "record": "104-10214-10034",
     "title": "CIA Inspector General's “Trujillo Report” on the assassination of Rafael Trujillo",
     "when": "Written circa spring 1967 · blacked out in an earlier release · reopened March 2025",
     "old": "https://www.archives.gov/files/research/jfk/releases/104-10214-10034.pdf",
     "what": "The CIA's internal inquiry into its role in the 1961 killing of Dominican dictator Rafael Trujillo.",
     "why": "Names and operational details were withheld to protect the people involved. The National Security "
            "Archive says the 2025 version names CIA officers and associates connected to the plot."},
    {"key": "westhem", "short": "CIA in Latin America", "record": "104-10301-10001",
     "title": "CIA Historical Staff: “Western Hemisphere Division, 1946–1965”",
     "when": "Written December 1973 · blacked out in an earlier release · reopened March 2025",
     "old": "https://www.archives.gov/files/research/jfk/releases/104-10301-10001.pdf",
     "what": "The CIA's own in-house history of two decades of operations across Latin America.",
     "why": "Spending figures and covert operations were kept secret as intelligence methods. The National Security "
            "Archive says the 2025 version reveals spending by country and influence operations in Bolivia."},
    {"key": "mexico", "short": "Mexico City station", "record": "104-10301-10010",
     "title": "CIA Inspector General's survey of the Mexico City station (extracts)",
     "when": "Written 1964 · blacked out in the 2022 release · reopened March 2025",
     "old": "https://www.archives.gov/files/research/jfk/releases/2022/104-10301-10010.pdf",
     "what": "An internal inspection of the CIA station that monitored Lee Harvey Oswald's visit to Mexico City "
             "weeks before the assassination.",
     "why": "How the station was organized and how it watched embassies were treated as protected methods for "
            "decades. The 2025 version shows more of that detail."},
]


def new_url_candidates(rec):
    return [NARA_2025.format(rec=rec, ext="pdf"), NARA_2025.format(rec=rec, ext="PDF")]


def _pdf(url):
    data, _ctype, _final = _fetch_bytes(url)
    if data[:5] != b"%PDF-":
        raise ValueError("not a PDF")
    return data


def _render(pdf, i, scale):
    return pdf[i].render(scale=scale).to_pil().convert("L")


def _png(img):
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def ink_drop(old_img, new_img):
    """How much black ink disappeared between two renderings of the same page (0 = none)."""
    import numpy as np
    w, h = min(old_img.width, new_img.width), min(old_img.height, new_img.height)
    a = np.asarray(old_img.resize((w, h))) < 70
    b = np.asarray(new_img.resize((w, h))) < 70
    return float((a & ~b).mean())


def find_reveal(case, max_pages=80):
    """{'page','pages','before','after','old','new','drop'}: PNG bytes of the most-changed page, before and after."""
    import pypdfium2 as pdfium
    old_bytes = _pdf(case["old"])
    new_bytes, new_url = None, None
    for u in new_url_candidates(case["record"]):
        try:
            new_bytes, new_url = _pdf(u), u
            break
        except Exception:
            continue
    if not new_bytes:
        raise LookupError("2025 version not found")
    old, new = pdfium.PdfDocument(old_bytes), pdfium.PdfDocument(new_bytes)
    n = min(len(old), len(new), max_pages)
    best, best_i = -1.0, 0
    for i in range(n):
        d = ink_drop(_render(old, i, 0.35), _render(new, i, 0.35))
        if d > best:
            best, best_i = d, i
    return {"page": best_i + 1, "pages": len(new), "drop": best,
            "before": _png(_render(old, best_i, 1.1)), "after": _png(_render(new, best_i, 1.1)),
            "old": case["old"], "new": new_url}
