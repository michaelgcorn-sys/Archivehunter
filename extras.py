"""
Extras for Archive Hunter 2.0:
  fbi_recent()      - newest files on the FBI Vault ("Recently Added")
  gwu_recent()      - newest National Security Archive postings (their RSS feed)
  daily_mystery()   - guess-the-codeword puzzle, a new one every day
  share_card()      - a "DECLASSIFIED" image of a document to post or text
"""

import io
import random
import re
import textwrap
import urllib.parse

from sources import _get, clean, search_cia

MODULE_VERSION = 56   # keep in step with APP_CODE_VERSION in app.py


# ── Fresh releases ───────────────────────────────────────────────────────────

def fbi_recent(limit=8):
    page = _get("https://vault.fbi.gov/recently-added", timeout=30).text
    skip = ("/search", "/login", "/reading-room-index", "/recently-added", "/sitemap", "/accessibility",
            "/contact", "/front-page", "/rss", "/portal_", "/acl_users", "/contact-info", "/help")
    out, seen = [], set()
    for href, title in re.findall(r'<a[^>]+href="(https://vault\.fbi\.gov/[^"#?]+)"[^>]*>(.*?)</a>', page, re.S):
        path = urllib.parse.urlparse(href).path.rstrip("/")
        t = clean(title)
        if not path or path.count("/") < 1 or path.startswith(skip) or href in seen or len(t) < 6:
            continue
        seen.add(href)
        out.append({"source": "FBI Vault", "title": t, "url": href})
        if len(out) >= limit:
            break
    return out


def gwu_recent(limit=6):
    xml = _get("https://nsarchive.gwu.edu/rss.xml", timeout=20).text
    out = []
    for item in re.findall(r"<item>(.*?)</item>", xml, re.S):
        t = re.search(r"<title>(.*?)</title>", item, re.S)
        l = re.search(r"<link>(.*?)</link>", item, re.S)
        d = re.search(r"<pubDate>(.*?)</pubDate>", item, re.S)
        if t and l:
            title = clean(re.sub(r"<!\[CDATA\[|\]\]>", "", t.group(1)))
            out.append({"source": "National Security Archive", "title": title, "url": l.group(1).strip(),
                        "date": " ".join((d.group(1) if d else "").split()[1:4])})
        if len(out) >= limit:
            break
    return out


# ── Daily mystery: which codeword was blacked out? ──────────────────────────
# codeword -> (family, one-line description with era). Wrong answers come mostly from the same family,
# so the year and the descriptions are what solve it.
MYSTERY = {
    "AQUATONE": ("aircraft", "the U-2 spy plane program, mid-1950s"),
    "IDEALIST": ("aircraft", "later U-2 operations, late 1950s–1970s"),
    "OXCART": ("aircraft", "the Mach-3 A-12 spy plane, 1960s"),
    "TAGBOARD": ("aircraft", "the D-21 spy drone, late 1960s"),
    "CORONA": ("satellite", "the first photo spy satellites, 1960–1972"),
    "GAMBIT": ("satellite", "high-resolution spy satellites, 1963–1984"),
    "HEXAGON": ("satellite", "the 'Big Bird' spy satellites, 1971–1986"),
    "MKULTRA": ("mind", "CIA mind-control and drug experiments, 1953–1973"),
    "ARTICHOKE": ("mind", "CIA interrogation experiments, early 1950s"),
    "GRILL FLAME": ("mind", "Army psychic spying (remote viewing), 1978–1983"),
    "STARGATE": ("mind", "the remote-viewing program's last name, 1991–1995"),
    "MONGOOSE": ("covert", "the secret war against Castro, 1961–1962"),
    "ZAPATA": ("covert", "the Bay of Pigs invasion plan, 1961"),
    "PHOENIX": ("covert", "the Vietnam counterinsurgency program, 1965–1972"),
    "CHAOS": ("covert", "CIA spying on U.S. antiwar groups, 1967–1974"),
    "VENONA": ("codes", "cracking Soviet spy cables, 1943–1980"),
    "AZORIAN": ("codes", "raising a sunken Soviet submarine, 1974"),
}
MYSTERY_POOL = list(MYSTERY)

# Jargon that turns up in CIA titles
JARGON = {
    "ELINT": "electronic intelligence: intercepting enemy radar and other signals",
    "SIGINT": "signals intelligence: intercepted communications and electronic signals",
    "COMINT": "communications intelligence: intercepted messages",
    "PHOTINT": "photo intelligence: analysis of reconnaissance photos",
    "HUMINT": "human intelligence: information from spies and sources",
    "NPIC": "National Photographic Interpretation Center, which analyzed spy photos",
    "DCI": "Director of Central Intelligence, the head of the CIA",
    "DDCI": "Deputy Director of Central Intelligence",
    "DDP": "the CIA's Directorate of Plans, its covert-operations arm",
    "DDS&T": "the CIA's science and technology directorate",
    "OSA": "Office of Special Activities, which ran the CIA's spy planes",
    "PFIAB": "President's Foreign Intelligence Advisory Board",
    "USIB": "U.S. Intelligence Board, which coordinated the spy agencies",
    "NRO": "National Reconnaissance Office, which runs spy satellites",
    "NSC": "National Security Council",
    "SNIE": "Special National Intelligence Estimate",
    "NIE": "National Intelligence Estimate: the agencies' joint forecast",
    "KGB": "the Soviet Union's security and spy service",
    "GRU": "Soviet military intelligence",
}


def jargon_in(text):
    return [(k, v) for k, v in JARGON.items() if re.search(r"(?<![A-Z])" + re.escape(k) + r"(?![A-Z])", text or "")]


def daily_mystery(day):
    """Today's puzzle (same all day): masked title, year, 4 options with descriptions, jargon notes.
    Code names rotate so none repeats until all have been used; each comeback picks a different document."""
    order = MYSTERY_POOL[:]
    random.Random("archive-hunter-rotation").shuffle(order)   # one fixed rotation: every code name, then repeat
    slot = day.toordinal() % len(order)
    rnd = random.Random(f"mystery-{day.isoformat()}")
    pool = order[slot:] + order[:slot]
    for answer in pool[:6]:                                   # first codeword that has a usable titled document
        docs = [r for r in search_cia(f'title:"{answer}"', limit=25)
                if re.search(r"\b" + re.escape(answer) + r"\b", r["title"], re.I)
                and len(r["title"]) > len(answer) + 12 and r["date"][:4].isdigit()]
        if not docs:
            continue
        doc = rnd.choice(docs)
        family = MYSTERY[answer][0]
        same = [c for c in MYSTERY_POOL if c != answer and MYSTERY[c][0] == family]
        other = [c for c in MYSTERY_POOL if MYSTERY[c][0] != family]
        wrong = rnd.sample(same, min(2, len(same)))
        wrong += rnd.sample(other, 3 - len(wrong))
        options = [answer] + wrong
        rnd.shuffle(options)
        parts = re.split(r"\b" + re.escape(answer) + r"\b", doc["title"], flags=re.I)
        return {"answer": answer, "options": [(o, MYSTERY[o][1]) for o in options], "title_parts": parts,
                "year": doc["date"][:4], "url": doc["url"], "jargon": jargon_in(doc["title"])}
    return None


# ── Share card ───────────────────────────────────────────────────────────────

def _font(names, size):
    from PIL import ImageFont
    for n in names:
        for base in ("/usr/share/fonts/truetype/dejavu/", ""):
            try:
                return ImageFont.truetype(base + n, size)
            except Exception:
                continue
    return ImageFont.load_default(size=size)


def share_card(title, date, agency, thumb_bytes=None, footer="ARCHIVE HUNTER · declassified records"):
    """PNG bytes: a 1080x1350 'DECLASSIFIED' card with the document's first page."""
    from PIL import Image, ImageDraw, ImageOps
    W, H = 1080, 1350
    img = Image.new("RGB", (W, H), (16, 15, 12))
    d = ImageDraw.Draw(img)
    mono = _font(["DejaVuSansMono-Bold.ttf"], 30)
    serif = _font(["DejaVuSerif-Bold.ttf", "DejaVuSerif.ttf"], 50)
    small = _font(["DejaVuSans.ttf"], 30)
    d.text((70, 60), "EXHIBIT A  ·  DECLASSIFIED", fill=(196, 84, 74), font=mono)
    top = 130
    if thumb_bytes:
        try:
            page = Image.open(io.BytesIO(thumb_bytes)).convert("L")
            page = ImageOps.autocontrast(page)
            scale = min(620 / page.width, 720 / page.height)
            page = page.resize((int(page.width * scale), int(page.height * scale)), Image.LANCZOS)
            px = (W - page.width) // 2
            img.paste(Image.new("RGB", (page.width + 20, page.height + 20), (60, 52, 36)), (px - 10, top - 10))
            img.paste(page.convert("RGB"), (px, top))
            top += page.height + 50
        except Exception:
            top += 20
    # stamp
    stamp = Image.new("RGBA", (560, 120), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stamp)
    sd.rectangle([4, 4, 555, 115], outline=(196, 40, 40, 235), width=8)
    sd.text((40, 28), "DECLASSIFIED", fill=(196, 40, 40, 235), font=_font(["DejaVuSansMono-Bold.ttf"], 62))
    stamp = stamp.rotate(-8, expand=True)
    img.paste(stamp, (W - stamp.width - 40, 120), stamp)
    y = max(top, 260)
    if not thumb_bytes:
        y = 380
    for line in textwrap.wrap(title, 26)[:4]:
        d.text((70, y), line, fill=(236, 217, 176), font=serif)
        y += 64
    d.text((70, y + 16), " · ".join(x for x in (agency, date) if x), fill=(185, 171, 140), font=small)
    d.line([(70, H - 110), (W - 70, H - 110)], fill=(90, 74, 46), width=2)
    d.text((70, H - 85), footer, fill=(200, 169, 110), font=mono)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def first_page_image(ident):
    """Bytes of a document's first page: a sharp page image when the Internet Archive has one, else its thumbnail."""
    for url in (f"https://archive.org/download/{ident}/page/n0_w800.jpg", f"https://archive.org/services/img/{ident}"):
        try:
            r = _get(url, timeout=20)
            if r.headers.get("content-type", "").startswith("image") and len(r.content) > 2000:
                return r.content
        except Exception:
            continue
    return None
