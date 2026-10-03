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
# Declassified / intelligence
# ════════════════════════════════════════════════════════════════════════════

def search_cia(q, limit=12):
    """CIA CREST reading room. Its search page is server-rendered (checked Oct 2026)."""
    page = _get("https://www.cia.gov/readingroom/search/site/" + urllib.parse.quote(q)).text
    out, seen = [], set()
    # Each hit: <h3 class="title"><a href="…/readingroom/document/…">Title</a></h3> … <p class="search-snippet">…</p>
    blocks = re.split(r'<li[^>]*class="[^"]*search-result', page)
    for b in blocks[1:] or [page]:
        m = re.search(r'href="((?:https://www\.cia\.gov)?/readingroom/(?:document|docs)/[^"#?]+)"[^>]*>(.*?)</a>',
                      b, re.S)
        if not m:
            continue
        href = m.group(1)
        href = href if href.startswith("http") else "https://www.cia.gov" + href
        if href in seen:
            continue
        seen.add(href)
        snip = re.search(r'class="search-snippet[^"]*"[^>]*>(.*?)</', b, re.S)
        is_pdf = href.lower().endswith(".pdf")
        out.append(_res("CIA", m.group(2), href, kind="Declassified CIA record",
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
    """The Black Vault document archive (WordPress search API)."""
    data = _get("https://www.theblackvault.com/documentarchive/wp-json/wp/v2/search",
                params={"search": q, "per_page": limit}).json()
    return [_res("Black Vault", d.get("title", ""), d.get("url", ""), kind="FOIA document archive",
                 doc_url=d.get("url")) for d in data if d.get("url")]


def search_muckrock(q, limit=10):
    data = _get("https://www.muckrock.com/api_v1/foia/",
                params={"q": q, "format": "json", "page_size": limit, "status": "done"}).json()
    out = []
    for item in data.get("results", []):
        u = item.get("absolute_url", "")
        url = "https://www.muckrock.com" + u if u.startswith("/") else u
        out.append(_res("MuckRock", item.get("title", ""), url, kind="Completed FOIA request",
                        date=item.get("datetime_done") or item.get("date_filed"), doc_url=url))
    return out


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
    "MuckRock": search_muckrock,
    "Internet Archive": search_internet_archive,
    "Library of Congress": search_loc,
    "NASA": search_nasa,
    "Dept of Energy": search_doe,
    "Wikimedia Commons": search_wikimedia,
}
# Declassified sources rank a little higher when relevance is otherwise equal.
SOURCE_WEIGHT = {"CIA": 3, "FBI Vault": 3, "GWU Natl Security Archive": 3, "Black Vault": 2,
                 "MuckRock": 2, "NASA": 1, "Dept of Energy": 1}


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


def find_passages(url: str, query: str, width: int = 240, max_hits: int = 30):
    """
    Reads the document at url and returns
        {"read_url", "pages", "chars", "hits": [(page, text, [(start, end), ...]), ...], "note"}
    Follows a web page to the first PDF on it when the page itself has no matches.
    """
    terms = sorted({t.lower() for t in terms_of(query)}, key=len, reverse=True)
    if not terms:
        return {"read_url": url, "pages": 0, "chars": 0, "hits": [], "note": "No search terms."}

    data, ctype, final = _fetch_bytes(url)
    pages, note = [], ""
    is_pdf = data[:5] == b"%PDF-" or "pdf" in ctype

    if not is_pdf:
        text_html = data.decode("utf-8", "replace")
        body = clean(text_html) if "html" in ctype or "<html" in text_html[:2000].lower() else text_html
        pages = [(None, body)]
        if not _hits_in(body, terms):
            pdf = _first_pdf_link(text_html, final)
            if pdf:
                data, ctype, final = _fetch_bytes(pdf)
                is_pdf = data[:5] == b"%PDF-"
    if is_pdf:
        pages = list(_pdf_pages(data))
        if sum(len(t.strip()) for _, t in pages) < 40 * max(1, len(pages)) // 4:
            note = ("This PDF is mostly scanned images with no text layer, so words "
                    "can't be searched. Open it and read it directly.")

    hits = []
    for pno, text in pages:
        text = re.sub(r"\s+", " ", text)
        low = text.lower()
        spots = sorted((m.start(), m.start() + len(t)) for t in terms for m in re.finditer(re.escape(t), low))
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
            "chars": sum(len(t) for _, t in pages), "hits": hits, "note": note}


def _hits_in(text, terms):
    low = text.lower()
    return any(t in low for t in terms)


# Sites with no usable search from a server — opened in the browser instead.
BROWSER_ONLY = [
    ("National Archives (JFK, RFK, MLK)", "https://catalog.archives.gov/search?q={q}"),
    ("Mary Ferrell Foundation", "https://www.google.com/search?q=site%3Amaryferrell.org+{q}"),
    ("DOJ Epstein Library", "https://www.google.com/search?q=site%3Ajustice.gov%2Fepstein+{q}"),
    ("WAR.GOV UFO files", "https://www.war.gov/ufo/"),
    ("State Dept FOIA", "https://www.google.com/search?q=site%3Afoia.state.gov+{q}"),
    ("FilesDropped", "https://www.google.com/search?q=site%3Afilesdropped.com+{q}"),
]

TEST_QUERIES = {"CIA": "MKUltra", "FBI Vault": "Roswell", "GWU Natl Security Archive": "MKUltra",
                "Black Vault": "UFO", "MuckRock": "CIA", "Internet Archive": "Warren Commission",
                "Library of Congress": "Kennedy", "NASA": "Apollo 11", "Dept of Energy": "Manhattan Project",
                "Wikimedia Commons": "Apollo 11"}
