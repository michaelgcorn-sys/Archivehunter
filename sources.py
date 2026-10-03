"""
Archive Hunter search engine.

Every search function takes a query string and returns a list of result dicts:
    source, title, url, date, kind, snippet,
    doc_url   - what "Find my terms inside" reads (page, PDF or text file); None if not readable
    file_url  - a direct file download, or None

Functions raise on failure so the app can show which sources are down.
"""

from __future__ import annotations

import html as htmllib
import io
import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# Bump together with APP_CODE_VERSION in app.py on every update, so a running
# server that still has an old copy of this file in memory reloads it.
CODE_VERSION = 17

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9",
           "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8"}
TIMEOUT = 20


def _get(url, **kw):
    headers = {**HEADERS, **kw.pop("headers", {})}
    r = requests.get(url, headers=headers, timeout=kw.pop("timeout", TIMEOUT), **kw)
    r.raise_for_status()
    return r


def clean(s: str) -> str:
    s = re.sub(r"<script.*?</script>|<style.*?</style>", " ", s or "", flags=re.S | re.I)
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def _res(source, title, url, date="", kind="", snippet="", doc_url=None, file_url=None):
    return {"source": source, "title": clean(title)[:160] or "(untitled)", "url": url,
            "date": str(date or "")[:4], "kind": kind, "snippet": clean(snippet)[:320],
            "doc_url": doc_url, "file_url": file_url}


# ════════════════════════════════════════════════════════════════════════════
# Web search limited to one site — used when a site's own search can't be read
# by a server (JavaScript-built results, bot blocking). Uses DuckDuckGo's
# plain-HTML results page, which needs no JavaScript.
# ════════════════════════════════════════════════════════════════════════════

# Search engines tack the site name onto titles, e.g. "… | CIA FOIA (foia.cia.gov)"
_SITE_SUFFIX = re.compile(r"\s*[|\-–]\s*(CIA FOIA \(foia\.cia\.gov\)|CIA FOIA|FBI|The Black Vault|MuckRock)\s*$", re.I)


def site_search(site, q, source, kind, limit=10, url_must_match=None):
    page = _get("https://html.duckduckgo.com/html/", params={"q": f"site:{site} {q}"}).text
    if "result__a" not in page and "anomaly" in page.lower():
        raise RuntimeError("web search asked for a captcha; try again in a minute")
    out, seen = [], set()
    domain = site.split("/")[0]
    anchors = list(re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', page, re.S))
    for k, m in enumerate(anchors):
        href, title = m.groups()
        rest = page[m.end(): anchors[k + 1].start() if k + 1 < len(anchors) else len(page)]
        href = htmllib.unescape(href)
        if "uddg=" in href:
            href = urllib.parse.unquote(re.search(r"uddg=([^&]+)", href).group(1))
        elif href.startswith("//"):
            href = "https:" + href
        if domain not in href or href in seen:
            continue
        if url_must_match and not re.search(url_must_match, href):
            continue
        title = _SITE_SUFFIX.sub("", clean(title))
        seen.add(href)
        snip = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', rest, re.S)
        is_pdf = href.lower().split("?")[0].endswith(".pdf")
        out.append(_res(source, title, href, kind=kind, snippet=snip.group(1) if snip else "",
                        doc_url=href, file_url=href if is_pdf else None))
        if len(out) >= limit:
            break
    return out


# ════════════════════════════════════════════════════════════════════════════
# Declassified / intelligence
# ════════════════════════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════════════════════════
# Hidden browser — for sites that build their pages with JavaScript.
# On Streamlit Cloud, Chromium comes from packages.txt. One page at a time,
# because the free server has about 1 GB of memory.
# ════════════════════════════════════════════════════════════════════════════

import shutil
import threading

_BROWSER_LOCK = threading.Lock()


def _chromium_path():
    for name in ("chromium", "chromium-browser", "google-chrome"):
        p = shutil.which(name)
        if p:
            return p
    return None  # let Playwright use its own downloaded browser (local testing)


def browser_html(url, wait_for=None, timeout_s=30):
    """Load url in headless Chromium, let its JavaScript run, return the final HTML."""
    from playwright.sync_api import sync_playwright
    with _BROWSER_LOCK, sync_playwright() as pw:
        exe = _chromium_path()
        browser = pw.chromium.launch(headless=True, executable_path=exe,
                                     args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
        try:
            page = browser.new_page(user_agent=UA, viewport={"width": 1280, "height": 900})
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_s * 1000)
            if wait_for:
                try:
                    page.wait_for_selector(wait_for, timeout=timeout_s * 1000)
                except Exception:
                    pass
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            return page.content()
        finally:
            browser.close()


# ════════════════════════════════════════════════════════════════════════════
# Declassified / intelligence
# ════════════════════════════════════════════════════════════════════════════

CIA_SEARCH = "https://www.cia.gov/readingroom/search/site/"
# Actual CIA documents live here; collection and landing pages don't count as results.
CIA_DOC_URL = r"/readingroom/(document|docs)/"


def search_cia(q, limit=12):
    """CIA CREST reading room, three ways, fastest first:
       1. plain request to the CIA's own full-text search
       2. the same page in a hidden browser (its results are built by JavaScript)
       3. a web search limited to the CIA reading room"""
    url = CIA_SEARCH + urllib.parse.quote(q)
    for how, fetch in (("CIA full-text search", lambda: _get(url).text),
                       ("CIA full-text search", lambda: browser_html(url, wait_for="a[href*='/readingroom/document/']"))):
        try:
            got = parse_cia(fetch(), limit, how)
            if got:
                return got
        except Exception:
            pass
    return site_search("cia.gov/readingroom", q, "CIA", "CIA record (via web search)", limit,
                       url_must_match=CIA_DOC_URL)


def parse_cia(page, limit=12, how="Declassified CIA record"):
    out, seen = [], set()
    # Usual hit: <li class="search-result"><h3 class="title"><a href="…/readingroom/document/…">Title</a></h3>
    #            … <p class="search-snippet">…</p></li>
    blocks = re.split(r'<li[^>]*class="[^"]*search-result', page)[1:]
    if not blocks:  # unknown layout: treat every document link as a hit
        blocks = re.split(r'(?=<a[^>]+href="(?:https://www\.cia\.gov)?/readingroom/(?:document|docs)/)', page)[1:]
    for b in blocks:
        m = re.search(r'href="((?:https://www\.cia\.gov)?/readingroom/(?:document|docs)/[^"#?]+)"[^>]*>(.*?)</a>',
                      b, re.S)
        if not m or len(clean(m.group(2))) < 3:
            continue
        href = m.group(1)
        href = href if href.startswith("http") else "https://www.cia.gov" + href
        if href in seen:
            continue
        seen.add(href)
        snip = re.search(r'class="search-snippet[^"]*"[^>]*>(.*?)</(?:p|div)>', b, re.S)
        is_pdf = href.lower().endswith(".pdf")
        out.append(_res("CIA", m.group(2), href, kind=how,
                        snippet=snip.group(1) if snip else "", doc_url=href,
                        file_url=href if is_pdf else None))
        if len(out) >= limit:
            break
    return out


def search_fbi(q, limit=12):
    """FBI Vault (Plone CMS) search."""
    page = _get("https://vault.fbi.gov/search", params={"SearchableText": q}).text
    section = page
    m = re.search(r'<dl[^>]*class="[^"]*searchResults[^"]*"[^>]*>(.*?)</dl>', page, re.S)
    if m:
        section = m.group(1)
    skip = ("/search", "/login", "/reading-room-index", "/recently-added", "/sitemap",
            "/accessibility", "/contact")
    out, seen = [], set()
    for href, title in re.findall(r'<a[^>]+href="(https://vault\.fbi\.gov/[^"#?]+)"[^>]*>(.*?)</a>', section, re.S):
        path = urllib.parse.urlparse(href).path.rstrip("/")
        t = clean(title)
        if not path or path.startswith(skip) or href in seen or len(t) < 4:
            continue
        seen.add(href)
        out.append(_res("FBI Vault", t, href, kind="FBI FOIA file", doc_url=href,
                        file_url=href + "/at_download/file" if "%20Part%20" in href else None))
        if len(out) >= limit:
            break
    return out


def search_gwu(q, limit=12):
    """GWU National Security Archive. Results link to /node/N (postings) and /media/N (documents)."""
    page = _get("https://nsarchive.gwu.edu/search", params={"s": q}).text
    out, seen = [], set()
    for href, kind, num, title in re.findall(
            r'<a[^>]+href="((?:https://nsarchive\.gwu\.edu)?/(node|media)/(\d+)[^"]*)"[^>]*>(.*?)</a>', page, re.S):
        t = clean(title)
        if len(t) < 8 or num in seen:
            continue
        seen.add(num)
        url = href if href.startswith("http") else "https://nsarchive.gwu.edu" + href
        is_doc = kind == "media"
        out.append(_res("GWU Natl Security Archive", t, url,
                        kind="Declassified document" if is_doc else "Briefing book / posting",
                        doc_url=url, file_url=url if is_doc else None))
        if len(out) >= limit:
            break
    return out


def search_blackvault(q, limit=10):
    """The Black Vault. Its built-in search API skips the document pages, so use a site web search."""
    return site_search("theblackvault.com/documentarchive", q, "Black Vault", "FOIA document archive", limit)


def search_muckrock(q, limit=10):
    """MuckRock. Its API started refusing servers (403) in 2026, so fall back to a site web search."""
    try:
        data = _get("https://www.muckrock.com/api_v1/foia/",
                    params={"q": q, "format": "json", "page_size": limit, "status": "done"}).json()
        out = []
        for item in data.get("results", []):
            u = item.get("absolute_url", "")
            url = "https://www.muckrock.com" + u if u.startswith("/") else u
            out.append(_res("MuckRock", item.get("title", ""), url, kind="Completed FOIA request",
                            date=item.get("datetime_done") or item.get("date_filed"), doc_url=url))
        if out:
            return out
    except Exception:
        pass
    return site_search("muckrock.com/foi", q, "MuckRock", "FOIA request", limit)


def search_doj_epstein(q, limit=10):
    """DOJ Epstein Library (justice.gov/epstein) via site web search."""
    return site_search("justice.gov/epstein", q, "DOJ Epstein Library", "DOJ release", limit)


# ════════════════════════════════════════════════════════════════════════════
# Libraries, science, media
# ════════════════════════════════════════════════════════════════════════════

def search_internet_archive(q, limit=12):
    params = {"q": q, "fl[]": ["identifier", "title", "mediatype", "date", "description"],
              "rows": limit, "output": "json"}
    data = _get("https://archive.org/advancedsearch.php", params=params).json()
    kinds = {"texts": "Document / book", "movies": "Video", "audio": "Audio", "image": "Image"}
    out = []
    for d in data.get("response", {}).get("docs", []):
        ident = d["identifier"]
        title = d.get("title", ident)
        desc = d.get("description", "")
        title = title[0] if isinstance(title, list) else title
        desc = desc[0] if isinstance(desc, list) else desc
        texts = d.get("mediatype") == "texts"
        out.append(_res("Internet Archive", title, f"https://archive.org/details/{ident}",
                        date=d.get("date"), kind=kinds.get(d.get("mediatype"), "Item"), snippet=desc,
                        doc_url=f"https://archive.org/download/{ident}/{ident}_djvu.txt" if texts else None,
                        file_url=f"https://archive.org/details/{ident}"))
    return out


def search_loc(q, limit=8):
    data = _get("https://www.loc.gov/search/", params={"q": q, "fo": "json", "c": limit}).json()
    out = []
    for it in data.get("results", []):
        url = it.get("url") or it.get("id", "")
        desc = it.get("description") or ""
        desc = desc[0] if isinstance(desc, list) and desc else desc
        out.append(_res("Library of Congress", it.get("title", ""), url, date=it.get("date"),
                        kind=(it.get("original_format") or ["Item"])[0], snippet=str(desc)))
    return out


def search_nasa(q, limit=10):
    r = requests.post("https://ntrs.nasa.gov/api/citations/search",
                      json={"q": q, "page": {"size": limit, "from": 0}},
                      headers={**HEADERS, "Accept": "application/json"}, timeout=TIMEOUT)
    r.raise_for_status()
    out = []
    for it in r.json().get("results", []):
        nid = it.get("id")
        pdf = None
        for d in it.get("downloads") or []:
            links = d.get("links") or {}
            p = links.get("pdf") or links.get("original") if isinstance(links, dict) else None
            if p:
                pdf = p if p.startswith("http") else "https://ntrs.nasa.gov" + p
                break
        pubs = it.get("publications") or [{}]
        date = (pubs[0] or {}).get("publicationDate") or it.get("created", "")
        out.append(_res("NASA", it.get("title", ""), f"https://ntrs.nasa.gov/citations/{nid}", date=date,
                        kind=str(it.get("stiType", "Report")).replace("_", " ").title(),
                        snippet=it.get("abstract", ""), doc_url=pdf, file_url=pdf))
    return out


def search_doe(q, limit=10):
    r = _get("https://www.osti.gov/api/v1/records", params={"q": q, "rows": limit},
             headers={**HEADERS, "Accept": "application/json"})
    data = r.json()
    out = []
    for it in data if isinstance(data, list) else data.get("records", []):
        oid = it.get("osti_id")
        view, pdf = f"https://www.osti.gov/biblio/{oid}", None
        for l in it.get("links") or []:
            if l.get("rel") == "citation":
                view = l.get("href", view)
            elif l.get("rel") == "fulltext":
                pdf = l.get("href")
        out.append(_res("Dept of Energy", it.get("title", ""), view, date=it.get("publication_date"),
                        kind=it.get("product_type", "Report"), snippet=it.get("description", ""),
                        doc_url=pdf, file_url=pdf))
    return out


def search_wikimedia(q, limit=8):
    data = _get("https://commons.wikimedia.org/w/api.php", params={
        "action": "query", "list": "search", "srsearch": q, "srnamespace": 6,
        "srlimit": limit, "format": "json"}).json()
    out = []
    for it in data.get("query", {}).get("search", []):
        t = it["title"]
        name = t.replace("File:", "")
        out.append(_res("Wikimedia Commons", name, "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(t),
                        kind="Public-domain image / scan", snippet=it.get("snippet", ""),
                        file_url="https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(name)))
    return out


SOURCES = {
    "CIA": search_cia,
    "FBI Vault": search_fbi,
    "GWU Natl Security Archive": search_gwu,
    "Black Vault": search_blackvault,
    "DOJ Epstein Library": search_doj_epstein,
    "MuckRock": search_muckrock,
    "Internet Archive": search_internet_archive,
    "Library of Congress": search_loc,
    "NASA": search_nasa,
    "Dept of Energy": search_doe,
    "Wikimedia Commons": search_wikimedia,
}
# Declassified sources rank a little higher when relevance is otherwise equal.
SOURCE_WEIGHT = {"CIA": 3, "FBI Vault": 3, "GWU Natl Security Archive": 3, "Black Vault": 2,
                 "DOJ Epstein Library": 2, "MuckRock": 2, "NASA": 1, "Dept of Energy": 1}


# ════════════════════════════════════════════════════════════════════════════
# Search everything + rank
# ════════════════════════════════════════════════════════════════════════════

def terms_of(q: str) -> list[str]:
    phrases = re.findall(r'"([^"]+)"', q)
    rest = re.sub(r'"[^"]+"', " ", q)
    words = [w for w in re.findall(r"[\w'-]+", rest) if len(w) > 2 or w.isdigit()]
    return phrases + words


def score(r, q):
    t, s = r["title"].lower(), r["snippet"].lower()
    terms = [x.lower() for x in terms_of(q)]
    pts = 6 if q.lower().strip('"') in t else 0
    pts += sum(2 for x in terms if x in t) + sum(1 for x in terms if x in s)
    if terms and all(x in t + " " + s for x in terms):
        pts += 3
    return pts + SOURCE_WEIGHT.get(r["source"], 0) + (1 if r["doc_url"] else 0)


def search_all(q: str, names: list[str]):
    """Returns (ranked results, {source: count or error string})."""
    results, status = [], {}
    with ThreadPoolExecutor(max_workers=len(names) or 1) as ex:
        futs = {ex.submit(SOURCES[n], q): n for n in names}
        for f in as_completed(futs):
            n = futs[f]
            try:
                got = f.result()
                results += got
                status[n] = len(got)
            except Exception as e:
                status[n] = f"{type(e).__name__}"
    results.sort(key=lambda r: score(r, q), reverse=True)
    return results, status


# ════════════════════════════════════════════════════════════════════════════
# Find my terms inside a document
# ════════════════════════════════════════════════════════════════════════════

MAX_BYTES = 40 * 1024 * 1024
MAX_PAGES = 600


def _fetch_bytes(url):
    with requests.get(url, headers=HEADERS, timeout=45, stream=True) as r:
        r.raise_for_status()
        buf = io.BytesIO()
        for chunk in r.iter_content(65536):
            buf.write(chunk)
            if buf.tell() > MAX_BYTES:
                raise ValueError("file is over 40 MB")
        return buf.getvalue(), r.headers.get("Content-Type", ""), r.url


def _pdf_pages(data):
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    for i, page in enumerate(reader.pages[:MAX_PAGES]):
        try:
            yield i + 1, page.extract_text() or ""
        except Exception:
            yield i + 1, ""


def _first_pdf_link(page_html, base):
    links = re.findall(r'href="([^"]+?\.pdf(?:\?[^"]*)?)"', page_html, re.I)
    # FBI Vault parts download via /at_download/file
    links += re.findall(r'href="([^"]+/at_download/file)"', page_html, re.I)
    # MuckRock attachments live on its CDN
    links += re.findall(r'(https://cdn\.muckrock\.com/[^"\'\s<>]+\.pdf)', page_html, re.I)
    return urllib.parse.urljoin(base, links[0]) if links else None


OCR_MAX_PAGES = 40      # character recognition is ~2-4 s a page on the free server
OCR_TIME_BUDGET = 150   # seconds


def _fetch_page(url):
    """Like _fetch_bytes, but if a site blocks plain requests, load its page in the hidden browser."""
    try:
        return _fetch_bytes(url)
    except requests.HTTPError as e:
        if e.response is None or e.response.status_code not in (401, 403, 406, 429, 503):
            raise
    html_text = browser_html(url)
    return html_text.encode("utf-8"), "text/html", url


def _ocr_pages(data):
    """Render each PDF page to an image and read it with Tesseract."""
    import time
    import pypdfium2 as pdfium
    import pytesseract
    pdf = pdfium.PdfDocument(data)
    start = time.time()
    for i in range(min(len(pdf), OCR_MAX_PAGES)):
        if time.time() - start > OCR_TIME_BUDGET:
            break
        img = pdf[i].render(scale=2.2).to_pil().convert("L")
        yield i + 1, pytesseract.image_to_string(img)


def find_passages(url: str, query: str, width: int = 240, max_hits: int = 30, ocr: bool = False):
    """
    Reads the document at url and returns
        {"read_url", "pages", "chars", "hits": [(page, text, [(start, end), ...]), ...],
         "note", "scanned"}
    Follows a web page to the first PDF on it when the page itself has no matches.
    With ocr=True, scanned PDFs (no text layer) are read with character recognition.
    """
    terms = sorted({t.lower() for t in terms_of(query)}, key=len, reverse=True)
    if not terms:
        return {"read_url": url, "pages": 0, "chars": 0, "hits": [], "note": "No search terms.",
                "scanned": False}

    # Dead or "page not found" document? Use the Wayback Machine's saved copy instead.
    wayback = None
    try:
        data, ctype, final = _fetch_page(url)
        if data[:5] != b"%PDF-" and _NOT_FOUND.search(data[:20000]):
            raise LookupError("page not found")
    except Exception:
        wayback = wayback_snapshot(url)
        if not wayback:
            raise
        data, ctype, final = _fetch_bytes(wayback["raw"])
    pages, note, scanned = [], "", False
    is_pdf = data[:5] == b"%PDF-" or "pdf" in ctype

    if not is_pdf:
        text_html = data.decode("utf-8", "replace")
        body = clean(text_html) if "html" in ctype or "<html" in text_html[:2000].lower() else text_html
        pages = [(None, body)]
        if not _hits_in(body, terms):
            pdf = _first_pdf_link(text_html, url if wayback else final)
            if pdf and wayback:
                pdf = f"https://web.archive.org/web/{wayback['timestamp']}id_/{pdf}"
            if pdf:
                data, ctype, final = _fetch_bytes(pdf)
                is_pdf = data[:5] == b"%PDF-"
    if is_pdf:
        pages = list(_pdf_pages(data))
        scanned = sum(len(t.strip()) for _, t in pages) < 10 * max(1, len(pages))
        if scanned and ocr:
            pages = list(_ocr_pages(data))
            total = len(list(_pdf_pages(data)))
            note = (f"Read {len(pages)} of {total} scanned pages with character recognition. "
                    "Old typewriter scans can have misread words.")
        elif scanned:
            note = "This PDF is scanned page images, so there's no text to search yet."

    hits = []
    for pno, text in pages:
        text = re.sub(r"\s+", " ", text)
        low = text.lower()
        spots, last_end = [], -1
        for s in sorted((m.start(), m.start() + len(t)) for t in terms for m in re.finditer(re.escape(t), low)):
            if s[0] >= last_end:  # drop overlapping matches (e.g. "mk" inside "mkultra")
                spots.append(s)
                last_end = s[1]
        i = 0
        while i < len(spots) and len(hits) < max_hits:
            a = max(0, spots[i][0] - width // 2)
            b = min(len(text), spots[i][1] + width // 2)
            marks = []
            while i < len(spots) and spots[i][0] < b:
                marks.append((spots[i][0] - a, spots[i][1] - a))
                b = min(len(text), max(b, spots[i][1] + width // 3))
                i += 1
            hits.append((pno, text[a:b], marks))
    return {"read_url": final, "pages": len(pages) if is_pdf else 0,
            "chars": sum(len(t) for _, t in pages), "hits": hits, "note": note,
            "scanned": scanned and not ocr, "wayback": wayback}


def _hits_in(text, terms):
    low = text.lower()
    return any(t in low for t in terms)


# Sites with no usable search from a server — opened in the browser instead.
BROWSER_ONLY = [
    ("National Archives (JFK, RFK, MLK)", "https://catalog.archives.gov/search?q={q}"),
    ("Mary Ferrell Foundation", "https://www.google.com/search?q=site%3Amaryferrell.org+{q}"),
    ("WAR.GOV UFO files", "https://www.war.gov/ufo/"),
    ("State Dept FOIA", "https://www.google.com/search?q=site%3Afoia.state.gov+{q}"),
    ("FilesDropped", "https://www.google.com/search?q=site%3Afilesdropped.com+{q}"),
]

TEST_QUERIES = {"CIA": "MKUltra", "FBI Vault": "Roswell", "GWU Natl Security Archive": "MKUltra",
                "Black Vault": "UFO", "DOJ Epstein Library": "Maxwell", "MuckRock": "CIA", "Internet Archive": "Warren Commission",
                "Library of Congress": "Kennedy", "NASA": "Apollo 11", "Dept of Energy": "Manhattan Project",
                "Wikimedia Commons": "Apollo 11"}


# ════════════════════════════════════════════════════════════════════════════
# Top Secret feed — documents whose own archive listing calls them TOP SECRET
# ════════════════════════════════════════════════════════════════════════════

_TS = re.compile(r"\btop[\s-]*secret\b|\bTS//|\bTS/SCI\b", re.I)


def _ia_top_secret(limit=60):
    # Government documents only: the item must be tagged or described as declassified /
    # intelligence / FOIA material, and anything tagged as fiction, novels or comics is excluded.
    gov = ('(subject:(declassified OR declassification OR "national security" OR intelligence OR CIA OR FBI '
           'OR NSA OR FOIA OR "freedom of information" OR "united states government" OR military) '
           'OR description:(declassified OR FOIA OR "freedom of information" OR "national archives"))')
    params = {"q": f'title:("top secret") AND mediatype:texts AND {gov} '
                   'AND NOT subject:(fiction OR novel OR novels OR comics OR pulp OR "science fiction")',
              "fl[]": ["identifier", "title", "date", "description"], "rows": limit,
              "output": "json", "sort[]": "downloads desc"}
    docs = _get("https://archive.org/advancedsearch.php", params=params).json()["response"]["docs"]
    out = []
    for d in docs:
        ident = d["identifier"]
        title = d.get("title", ident)
        title = title[0] if isinstance(title, list) else title
        r = _res("Internet Archive", title, f"https://archive.org/details/{ident}", date=d.get("date"),
                 kind="Document", doc_url=f"https://archive.org/download/{ident}/{ident}_djvu.txt")
        r["thumb"] = f"https://archive.org/services/img/{ident}"
        out.append(r)
    return out


def _wikimedia_top_secret(limit=40):
    data = _get("https://commons.wikimedia.org/w/api.php", params={
        "action": "query", "list": "search", "srsearch": ('intitle:"top secret" (declassified OR memorandum OR CIA OR NSA OR FBI '
                     'OR "Department of" OR "Joint Chiefs" OR military OR government)'), "srnamespace": 6,
        "srlimit": limit, "format": "json"}).json()
    out = []
    for it in data.get("query", {}).get("search", []):
        name = it["title"].replace("File:", "")
        r = _res("Wikimedia Commons", re.sub(r"\.(jpe?g|png|tiff?|pdf|gif)$", "", name, flags=re.I),
                 "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(it["title"]),
                 kind="Scanned document", snippet=it.get("snippet", ""))
        r["thumb"] = ("https://commons.wikimedia.org/wiki/Special:FilePath/"
                      + urllib.parse.quote(name) + "?width=320")
        out.append(r)
    return out


def top_secret_pool():
    """Pool of documents marked TOP SECRET, drawn from several archives at once.
    Internet Archive is left out on purpose: its matches are mostly books, not documents.
    A document qualifies only if 'TOP SECRET' (or TS//, TS/SCI) is in its own title or description."""
    jobs = {
        "CIA": lambda: search_cia('"top secret"', limit=20),
        "GWU": lambda: search_gwu("top secret", limit=25),
        "Wikimedia": _wikimedia_top_secret,
        "Dept of Energy": lambda: search_doe('"top secret"', limit=20),
    }
    pool, seen = [], set()
    with ThreadPoolExecutor(max_workers=len(jobs)) as ex:
        for f in as_completed([ex.submit(fn) for fn in jobs.values()]):
            try:
                for r in f.result():
                    if r["url"] in seen or not _TS.search(r["title"] + " " + r["snippet"]):
                        continue
                    seen.add(r["url"])
                    r.setdefault("thumb", None)
                    pool.append(r)
            except Exception:
                pass
    # Drop cards whose link is dead or bounces to a front page
    with ThreadPoolExecutor(max_workers=16) as ex:
        dead = list(ex.map(lambda r: _is_gone(r["url"]), pool))
    return [r for r, d in zip(pool, dead) if not d]


# ════════════════════════════════════════════════════════════════════════════
# Wayback Machine — saved copies of pages that are gone or changed
# ════════════════════════════════════════════════════════════════════════════

def saved_copy_url(url):
    """Most recent Wayback Machine copy of a page (the Wayback Machine redirects to it)."""
    return "https://web.archive.org/web/2/" + url


def wayback_snapshot(url):
    """Closest saved copy of url, or None. Official, free availability API."""
    d = _get("https://archive.org/wayback/available", params={"url": url}, timeout=15).json()
    c = (d.get("archived_snapshots") or {}).get("closest") or {}
    if not c.get("available"):
        return None
    ts = c["timestamp"]
    return {"timestamp": ts, "date": f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}",
            "view": f"https://web.archive.org/web/{ts}/{url}",
            "raw": f"https://web.archive.org/web/{ts}id_/{url}"}   # id_ = the original file, no Wayback toolbar


_NOT_FOUND = re.compile(rb"<title>[^<]{0,80}(not found|404|page cannot be found|no longer available)", re.I)

# Government sites the Vanished Files search digs through
VANISHED_DOMAINS = ["cia.gov", "fbi.gov", "nsa.gov", "defense.gov", "war.gov", "aaro.mil",
                    "state.gov", "archives.gov", "justice.gov", "dni.gov"]


def _cdx(domain, pattern):
    """Wayback Machine index: saved pages on a domain whose web address matches pattern."""
    params = [("url", domain), ("matchType", "domain"), ("output", "json"),
              ("fl", "original,timestamp,mimetype"), ("filter", "statuscode:200"),
              ("filter", "mimetype:(text/html|application/pdf)"), ("filter", "original:" + pattern),
              ("collapse", "urlkey"), ("limit", "150")]
    r = requests.get("https://web.archive.org/cdx/search/cdx", params=params, headers=HEADERS, timeout=35)
    r.raise_for_status()
    rows = r.json() if r.text.strip() else []
    return rows[1:] if rows else []


def _is_gone(url):
    """True only when we're confident the page no longer exists on the live site."""
    try:
        with requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True, stream=True) as r:
            head = next(r.iter_content(8192), b"")
            if r.status_code in (404, 410):
                return True
            if r.status_code >= 400:
                return False      # blocked or server trouble: can't tell, so don't claim it's gone
            orig_path = urllib.parse.urlparse(url).path.strip("/")
            final_path = urllib.parse.urlparse(r.url).path.strip("/")
            if orig_path and final_path in ("", "index.html", "home"):
                return True       # quietly redirected to the homepage
            if (orig_path and final_path != orig_path and orig_path.startswith(final_path)
                    and final_path.count("/") < orig_path.count("/")):
                return True       # bounced up to a section front page
            return bool(_NOT_FOUND.search(head))
    except Exception:
        return False


def _title_from_url(url):
    path = urllib.parse.unquote(urllib.parse.urlparse(url).path).rstrip("/")
    name = path.split("/")[-1] or path
    name = re.sub(r"\.(pdf|html?|aspx?|php)$", "", name, flags=re.I)
    name = re.sub(r"[-_+]+", " ", name).strip()
    return name[:1].upper() + name[1:] if name else url


def vanished_pages(q, limit=15):
    """Government pages whose web address matches the search, that the Wayback Machine saved,
    and that are gone from the live site now. Returns (results, domains_searched_ok)."""
    words = [w for t in terms_of(q) for w in re.findall(r"\w+", t)]
    if not words:
        return [], 0
    pattern = "(?i).*" + "[^/]*".join(re.escape(w) for w in words) + ".*"
    cands, ok = {}, 0
    with ThreadPoolExecutor(max_workers=len(VANISHED_DOMAINS)) as ex:
        futs = {ex.submit(_cdx, d, pattern): d for d in VANISHED_DOMAINS}
        for f in as_completed(futs):
            try:
                rows = f.result()
                ok += 1
            except Exception:
                continue
            for original, ts, mime in rows:
                key = re.sub(r"^https?://(www\.)?|:80(?=/)", "", original).rstrip("/").lower()
                if key not in cands or ts > cands[key][1]:
                    cands[key] = (original.replace(":80/", "/"), ts, mime, futs[f])
    # PDFs first (more likely to be actual documents), newest first, then check which are gone
    order = sorted(cands.values(), key=lambda c: (c[2] != "application/pdf", -int(c[1][:8])))[:60]
    with ThreadPoolExecutor(max_workers=16) as ex:
        gone = list(ex.map(lambda c: _is_gone(c[0]), order))
    out = []
    for (url, ts, mime, domain), is_gone in zip(order, gone):
        if not is_gone:
            continue
        date = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"
        raw = f"https://web.archive.org/web/{ts}id_/{url}"
        r = _res(f"Vanished from {domain}", _title_from_url(url), f"https://web.archive.org/web/{ts}/{url}",
                 date=ts, kind=f"{'PDF' if mime == 'application/pdf' else 'Web page'} · gone from the live site · saved {date}",
                 snippet=url, doc_url=raw, file_url=raw if mime == "application/pdf" else None)
        out.append(r)
        if len(out) >= limit:
            break
    return out, ok
