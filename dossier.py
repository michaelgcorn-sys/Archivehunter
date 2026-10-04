"""
Dossier: everything shown when someone opens a single CIA document inside Archive Hunter.

  load_dossier(ident)  -> title, date, picture of page 1, links, text excerpt, trail terms, folder neighbors
  extract_terms(text)  -> codewords, people and places pulled from the document's own text
  folder_neighbors()   -> documents filed next to it (CIA "RDP" numbers encode job, box and folder)

Works on the Internet Archive's mirror of the CIA reading room (collection "ciareadingroom").
"""

import re

MODULE_VERSION = 48   # keep in step with APP_CODE_VERSION in app.py
from collections import Counter

from sources import _get, clean, search_cia, strip_release_stamp, text_quality

IDENT_RE = re.compile(r"^cia-readingroom-document-[a-z0-9-]{4,60}$")


def is_cia_ident(s):
    return bool(s and IDENT_RE.match(s))


def ident_from_url(url):
    m = re.search(r"archive\.org/(?:details|download)/(cia-readingroom-document-[a-z0-9-]+)", url or "")
    return m.group(1) if m else None


# ── Trail terms ──────────────────────────────────────────────────────────────

# Well-known program names and cryptonyms. Shown first when they appear in a document.
KNOWN_CODEWORDS = [
    "MKULTRA", "MKSEARCH", "MKNAOMI", "MKDELTA", "ARTICHOKE", "BLUEBIRD", "CORONA", "ARGON", "LANYARD",
    "GAMBIT", "HEXAGON", "KEYHOLE", "AQUATONE", "IDEALIST", "OXCART", "TAGBOARD", "CHALICE", "AZORIAN",
    "STARGATE", "GRILL FLAME", "SUN STREAK", "CENTER LANE", "GONDOLA WISH", "MHCHAOS", "CHAOS",
    "MONGOOSE", "ZAPATA", "PBSUCCESS", "PBFORTUNE", "TPAJAX", "HTLINGUAL", "KUBARK", "PHOENIX",
    "AMLASH", "ZRRIFLE", "VENONA", "NORTHWOODS", "ABLE ARCHER", "BLACKSHIELD", "SKYLARK", "TALENT",
    "RAINBOW", "TACKSMAN", "JENNIFER", "MOCKINGBIRD", "PAPERCLIP", "BLUE BOOK", "GRUDGE", "SIGN",
    "REMOTE VIEWING", "COINTELPRO", "INSCOM",
]
_KNOWN_WEAK = {"TALENT", "RAINBOW", "SIGN", "CHAOS", "PHOENIX", "JENNIFER", "GRUDGE", "SKYLARK"}  # common words too

PLACES = [
    "Soviet Union", "USSR", "Moscow", "Leningrad", "Cuba", "Havana", "Berlin", "East Germany", "West Germany",
    "Vietnam", "Saigon", "Hanoi", "Laos", "Cambodia", "China", "Peking", "Beijing", "Taiwan", "Korea",
    "Pyongyang", "Japan", "Iran", "Tehran", "Iraq", "Baghdad", "Israel", "Egypt", "Cairo", "Syria", "Lebanon",
    "Beirut", "Turkey", "Afghanistan", "Kabul", "Pakistan", "India", "Indonesia", "Philippines", "Guatemala",
    "Chile", "Santiago", "Nicaragua", "Panama", "Mexico", "Mexico City", "Brazil", "Argentina", "Congo",
    "Angola", "Libya", "Algeria", "Poland", "Warsaw", "Hungary", "Budapest", "Czechoslovakia", "Prague",
    "Yugoslavia", "Albania", "Romania", "Bulgaria", "Greece", "Italy", "Rome", "France", "Paris", "London",
    "Vienna", "Geneva", "Tibet", "Mongolia", "Area 51", "Groom Lake", "Nevada", "Los Alamos", "Langley",
    "Pentagon", "Dallas", "Roswell", "Guantanamo", "Fort Meade", "Fort Detrick",
]

_TITLES = r"(?:Mr|Mrs|Miss|Dr|Gen|General|Col|Colonel|Maj|Major|Capt|Captain|Adm|Admiral|Ambassador|President|" \
          r"Senator|Secretary|Premier|Chairman|Minister|Director|Professor|Prof)"

# Words that look important in a memo (headings, stamps, classification marks) but make poor searches
_STOP = set("""
SECRET TOP CONFIDENTIAL UNCLASSIFIED CLASSIFIED RESTRICTED SENSITIVE NOFORN ORCON NOCONTRACT EYES ONLY
APPROVED RELEASE RELEASED SANITIZED COPY DECLASSIFIED PART CENTRAL INTELLIGENCE AGENCY MEMORANDUM SUBJECT
REFERENCE REFERENCES DATE FROM THRU ATTENTION ATTN DISTRIBUTION ORIG INFO CABLE MESSAGE CITE PAGE PAGES
OFFICE DIRECTOR DEPUTY ASSISTANT CHIEF STAFF DIVISION BRANCH SECTION ANNEX ENCLOSURE ATTACHMENT FORM
REPORT REPORTS SUMMARY DRAFT FILE FILES COPIES NUMBER UNITED STATES GOVERNMENT AMERICAN SOVIET COMMUNIST
DOCUMENT DOCUMENTS RECORD RECORDS INFORMATION ADMINISTRATIVE OFFICER OFFICERS OPERATIONAL OPERATIONS
REQUIREMENTS REQUEST LETTER LIST STATUS GENERAL SPECIAL SERVICE SERVICES PERSONNEL SUPPORT COMMITTEE
MEETING MINUTES PLAN PLANS POLICY STUDY ANALYSIS ESTIMATE INTELLIGENCE INFORMATION AIRGRAM DISPATCH TELEGRAM
SESSION SESSIONS NATIONAL NATIONALS REMOTE VIEWING VIEWER VIEWERS TARGET TARGETS AREA AREAS RESULT RESULTS
SOURCE SOURCES SUBJECTS TRANSCRIPT INTERVIEW QUESTION ANSWER COMMENTS DESCRIPTION IMPRESSIONS PERCEPTIONS
CIA FBI NSA DIA DOD USA USAF ARMY
THE AND FOR WITH THAT THIS WHICH WILL HAVE BEEN FROM WERE THEY THEIR THERE ALSO OTHER INTO UPON SUCH
THAN THEN THESE THOSE WOULD SHOULD COULD ABOUT AFTER BEFORE BEING UNDER OVER SOME MORE MOST MUST
ONLY VERY WHEN WHERE WHAT WHO WHOM WHOSE ANY ALL EACH BOTH SAID SAME HAS HAD NOT ARE WAS ITS
JANUARY FEBRUARY MARCH APRIL MAY JUNE JULY AUGUST SEPTEMBER OCTOBER NOVEMBER DECEMBER
MONDAY TUESDAY WEDNESDAY THURSDAY FRIDAY SATURDAY SUNDAY
STAT STATINTL STATSPEC USE INTERNAL NOTE NOTES TABLE FIGURE ROUTING SLIP ACTION REMARKS NAME
ADDRESS ROOM BLDG EXT TEL PHONE SIGNATURE SIGNED YES NO NONE TOTAL ITEM ITEMS PARA PARAGRAPH
SERIES REGISTRY CONTROL CONTROLLED HANDLE VIA CHANNELS CHANNEL SYSTEM SYSTEMS PROGRAM PROJECT
PRESIDENT DAILY BRIEF CHECKLIST BULLETIN WEEKLY REVIEW NATIONAL SECURITY COUNCIL DEPARTMENT STATE
DEFENSE ARMY NAVY FORCE FORCES AIR MILITARY GENERAL POLITICAL ECONOMIC
""".split())


def _plausible_word(w):
    """OCR produces junk like 'IIIL' or 'TTTT'. Keep tokens that look like real words or codewords."""
    if not re.fullmatch(r"[A-Za-z][A-Za-z-]{2,20}", w):
        return False
    u = w.upper()
    if not re.search(r"[AEIOUY]", u) and len(u) > 4:      # acronyms like USSR are fine; long vowelless runs are junk
        return False
    if re.search(r"(.)\1\1", u):                          # three of the same letter in a row
        return False
    return True


def extract_terms(text, title="", limit=10):
    """Pull search-worthy terms out of a document: codewords, people, places, then other ALL-CAPS names.
    Returns [(term, kind)] with kind in {'codeword', 'person', 'place', 'name'}."""
    body = f"{title}\n{text or ''}"[:200_000]
    letters = re.findall(r"[A-Za-z]", body)
    upper_ratio = sum(c.isupper() for c in letters) / max(1, len(letters))
    U = body.upper()
    found, seen = [], set()

    def add(term, kind):
        k = term.upper()
        if k not in seen:
            seen.add(k)
            found.append((term, kind))

    # 1. Known codewords, most mentioned first (weak ones must appear twice, or in the title)
    hits = []
    for cw in KNOWN_CODEWORDS:
        n = len(re.findall(r"\b" + re.escape(cw) + r"\b", U)) + (3 if cw in title.upper() else 0)
        if n and (cw not in _KNOWN_WEAK or n >= 2):
            hits.append((n, cw))
    for n, cw in sorted(hits, key=lambda x: -x[0]):
        add(cw, "codeword")

    # 2. People: a title followed by a surname
    if upper_ratio < 0.6:
        people = re.findall(_TITLES + r"\.?\s+((?:[A-Z]\.\s*)?[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?)", body)
    else:
        people = [p.title() for p in re.findall(_TITLES.upper() + r"\.?\s+([A-Z]{3,})", U)]   # surname only
    for p, n in Counter(p.strip() for p in people).most_common(4):
        last = p.split()[-1].upper()
        if last not in _STOP and _plausible_word(last):
            add(p, "person")

    # 3. Places
    counts = []
    for pl in PLACES:
        n = len(re.findall(r"\b" + re.escape(pl.upper()) + r"\b", U))
        if n:
            counts.append((n, pl))
    for n, pl in sorted(counts, key=lambda x: -x[0])[:4]:
        add(pl, "place")

    # 4. Other ALL-CAPS names in mixed-case text (codewords, acronyms, operation names)
    if upper_ratio < 0.6:
        caps = [w for w in re.findall(r"\b[A-Z][A-Z]{3,14}\b(?!-)", body)          # whole words, not "CIA-" fragments
                if w not in _STOP and _plausible_word(w)]
        title_words = set(re.findall(r"\b[A-Z][A-Z-]{3,14}\b", title or ""))
        for w, n in Counter(caps).most_common(8):
            if n - (1 if w in title_words else 0) >= 2:      # must recur in the body, not just the title
                add(w, "name")

    # drop single words that are part of a longer codeword already found (GRILL, FLAME of GRILL FLAME)
    multi = {w for t, k in found if k == "codeword" and " " in t for w in t.split()}
    found = [(t, k) for t, k in found if not (k != "codeword" and t.upper() in multi)
             and not (k == "codeword" and " " not in t and t in multi)]
    order = {"codeword": 0, "person": 1, "place": 2, "name": 3}
    return sorted(found, key=lambda t: order[t[1]])[:limit]


# ── Folder neighbors ─────────────────────────────────────────────────────────
# CIA-RDP78B03824A000500020028-0  =  job 78B03824A, then box / folder / document digits.
_RDP = re.compile(r"^cia-readingroom-document-(cia-rdp\d{2}[a-z]\d{5}[a-z])(\d{12})-\d$")


def folder_neighbors(ident, limit=10):
    """Documents with the same job, box and folder digits: filed next to this one."""
    m = _RDP.match(ident or "")
    if not m:
        return []
    prefix = f"cia-readingroom-document-{m.group(1)}{m.group(2)[:8]}"
    res = search_cia(f"identifier:{prefix}*", limit=limit + 1, sort="identifier asc")
    return [r for r in res if ident_from_url(r["url"]) != ident][:limit]


# ── Load everything for one document ─────────────────────────────────────────

def load_dossier(ident):
    if not is_cia_ident(ident):
        raise ValueError("not a CIA reading-room document")
    meta = _get(f"https://archive.org/metadata/{ident}", timeout=20).json().get("metadata", {})
    doc_id = ident.replace("cia-readingroom-document-", "")

    def one(v):
        return (v[0] if isinstance(v, list) and v else v) or ""
    title = re.sub(r"^CIA Reading Room \S+:\s*", "", clean(str(one(meta.get("title"))))).strip()
    desc = strip_release_stamp(clean(str(one(meta.get("description")))))
    if not title or title.upper() == "(UNTITLED)":
        title = (desc[:90] + "…") if desc and text_quality(desc[:200]) >= 0.85 else f"Untitled CIA document {doc_id.upper()}"
    files = f"https://archive.org/download/{ident}/{doc_id}"
    try:
        text = _get(files + "_djvu.txt", timeout=25).text[:300_000]
    except Exception:
        text = desc
    return {
        "ident": ident, "doc_id": doc_id.upper(), "title": title, "date": str(one(meta.get("date")))[:10],
        "thumb": f"https://archive.org/services/img/{ident}",
        "view": f"https://archive.org/details/{ident}", "pdf": files + ".pdf", "txt": files + "_djvu.txt",
        "excerpt": desc[:600] if text_quality(desc[:600]) >= 0.85 else "",   # hide garbled scan text
        "readable": text_quality(strip_release_stamp(text[:3000])) >= 0.85,
        "text": text,
        "terms": extract_terms(text, title),
    }
