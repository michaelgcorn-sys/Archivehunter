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
import random
import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# Bump together with APP_CODE_VERSION in app.py on every update, so a running
# server that still has an old copy of this file in memory reloads it.
CODE_VERSION = 40

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
# by a server (JavaScript-built results, bot blocking). Free search engines often
# block shared cloud servers with a captcha, so several are tried in turn.
# ════════════════════════════════════════════════════════════════════════════

import base64
import time as _time

# Search engines tack the site name onto titles, e.g. "… | CIA FOIA (foia.cia.gov)"
_SITE_SUFFIX = re.compile(r"\s*[|\-–]\s*(CIA FOIA \(foia\.cia\.gov\)|CIA FOIA|FBI|The Black Vault|MuckRock)\s*$", re.I)
import threading as _thr
_WEB_SEARCH_SLOTS = _thr.Semaphore(2)


def _unwrap(href):
    href = htmllib.unescape(href)
    if "uddg=" in href:                                   # DuckDuckGo redirect link
        return urllib.parse.unquote(re.search(r"uddg=([^&]+)", href).group(1))
    if "bing.com/ck/a" in href:                           # Bing click-tracking link, base64 inside
        u = re.search(r"[?&]u=a1([^&]+)", href)
        if u:
            raw = u.group(1)
            return base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode("utf-8", "replace")
    return "https:" + href if href.startswith("//") else href


def _parse_ddg_html(page):
    anchors = list(re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', page, re.S))
    for k, m in enumerate(anchors):
        rest = page[m.end(): anchors[k + 1].start() if k + 1 < len(anchors) else len(page)]
        snip = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', rest, re.S)
        yield m.group(1), m.group(2), snip.group(1) if snip else ""


def _parse_ddg_lite(page):
    anchors = list(re.finditer(r'<a[^>]+href="([^"]+)"[^>]*class=[\'"]result-link[\'"][^>]*>(.*?)</a>', page, re.S))
    for k, m in enumerate(anchors):
        rest = page[m.end(): anchors[k + 1].start() if k + 1 < len(anchors) else len(page)]
        snip = re.search(r"class=['\"]result-snippet['\"][^>]*>(.*?)</td>", rest, re.S)
        yield m.group(1), m.group(2), snip.group(1) if snip else ""


def _parse_bing(page):
    for block in re.split(r'<li class="b_algo', page)[1:]:
        m = re.search(r'<h2[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, re.S)
        if m:
            snip = re.search(r"<p[^>]*>(.*?)</p>", block, re.S)
            yield m.group(1), m.group(2), snip.group(1) if snip else ""


def _parse_mojeek(page):
    for block in re.split(r"<li[ >]", page)[1:]:
        m = re.search(r'<a[^>]+class="title"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, re.S) or \
            re.search(r'<h2[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, re.S)
        if m:
            snip = re.search(r'<p class="s"[^>]*>(.*?)</p>', block, re.S)
            yield m.group(1), m.group(2), snip.group(1) if snip else ""


_ENGINES = [   # (name, url, query parameter name, parser)
    ("DuckDuckGo", "https://html.duckduckgo.com/html/", "q", _parse_ddg_html),
    ("DuckDuckGo Lite", "https://lite.duckduckgo.com/lite/", "q", _parse_ddg_lite),
    ("Bing", "https://www.bing.com/search", "q", _parse_bing),
    ("Mojeek", "https://www.mojeek.com/search", "q", _parse_mojeek),
]


def web_search(query):
    """Returns (engine name, [(url, title, snippet), ...]). Tries each engine until one answers."""
    problems = []
    for name, url, param, parse in _ENGINES:
        try:
            page = _get(url, params={param: query}, timeout=15).text
            hits = [(_unwrap(h), t, s) for h, t, s in parse(page)]
            if hits:
                return name, hits
            problems.append(f"{name}: " + ("captcha" if re.search(r"captcha|anomaly|unusual traffic", page, re.I)
                                            else "no results"))
        except Exception as e:
            problems.append(f"{name}: {type(e).__name__}")
        _time.sleep(0.3)
    raise RuntimeError("every search engine refused (" + "; ".join(problems) + ")")


def site_search(site, q, source, kind, limit=10, url_must_match=None, hint=""):
    """site can include a section, e.g. "justice.gov/epstein". Bing and Mojeek ignore sections in
    site:, so the query uses the bare domain (plus an optional hint word) and the section is
    checked here instead."""
    domain, _, section = site.partition("/")
    with _WEB_SEARCH_SLOTS:
        engine, hits = web_search(f"site:{domain} {hint} {q}".replace("  ", " "))
    out, seen = [], set()
    for href, title, snip in hits:
        if domain not in href or href in seen:
            continue
        if section and f"/{section}" not in href:
            continue
        if url_must_match and not re.search(url_must_match, href):
            continue
        seen.add(href)
        is_pdf = href.lower().split("?")[0].endswith(".pdf")
        out.append(_res(source, _SITE_SUFFIX.sub("", clean(title)), href, kind=f"{kind} · found via {engine}",
                        snippet=snip, doc_url=href, file_url=href if is_pdf else None))
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


def search_cia(q, limit=15, page=1, sort=None):
    """CIA CREST reading room, searched through the Internet Archive's mirror of it
    (collection "ciareadingroom"). As of Oct 2026, cia.gov reading room addresses (search
    AND individual document pages) redirect to the reading room front page, so the mirror is
    the only reliable way to reach the documents. Each item has the original PDF plus full text."""
    params = {"q": f"({q}) AND collection:ciareadingroom",
              "fl[]": ["identifier", "title", "date", "description"], "rows": limit, "page": page, "output": "json"}
    if sort:
        params["sort[]"] = sort
    docs = _get("https://archive.org/advancedsearch.php", params=params).json()["response"]["docs"]
    out = []
    for d in docs:
        ident = d["identifier"]
        doc_id = ident.replace("cia-readingroom-document-", "")
        title = d.get("title", "")
        title = title[0] if isinstance(title, list) else title
        title = re.sub(r"^CIA Reading Room \S+:\s*", "", title).strip()
        desc = d.get("description", "")
        desc = desc[0] if isinstance(desc, list) else desc
        desc = re.sub(r"^\s*Approved For Release[^0-9]*[\d/ :-]+\s*", "", clean(desc), flags=re.I)
        if not title or title.upper() == "(UNTITLED)":
            body = re.sub(r"^\s*0*" + re.escape(doc_id) + r"\s*", "", desc, flags=re.I)   # drop the ID stamp
            title = (body[:90] + ("…" if len(body) > 90 else "")) if body else f"Untitled CIA document {doc_id.upper()}"
        files = f"https://archive.org/download/{ident}/{doc_id}"
        out.append(_res("CIA", title, f"https://archive.org/details/{ident}", date=d.get("date"),
                        kind=f"CIA document {doc_id.upper()}", snippet=desc,
                        doc_url=files + "_djvu.txt", file_url=files + ".pdf"))
    return out


# Under Kennedy the brief was the "President's Intelligence Checklist"; it became the PDB in Dec 1964.
PDB_QUERY = 'title:("president\'s daily brief" OR "intelligence checklist")'
PDB_FIRST, PDB_LAST = "1961-06-01", "1977-01-20"   # the released run: Kennedy through Ford (CIA, 2015-16)


def search_pdb(day, window=4, limit=12, widen=(30, 120)):
    """President's Daily Briefs from the CIA mirror (~3,965 of them, Oct 2026) dated within a few
    days of `day` (YYYY-MM-DD), earliest first. Briefs weren't issued every day, so a window is used."""
    from datetime import date, timedelta
    d = date.fromisoformat(day)
    for w in (window, *widen):      # if nothing near that date, look further out
        lo, hi = (d - timedelta(days=w)).isoformat(), (d + timedelta(days=w)).isoformat()
        res = search_cia(f"{PDB_QUERY} AND date:[{lo} TO {hi}]", limit=limit if w == window else 40,
                         sort="date asc")
        if res:
            break
    return sorted(res, key=lambda r: abs((date.fromisoformat((r["date"] or day)[:10]) - d).days))[:limit]


def diagnose_cia(q="MKUltra"):
    """For the archive check: the mirror, and what cia.gov itself does now."""
    lines = []
    try:
        n = _get("https://archive.org/advancedsearch.php",
                 params={"q": f"({q}) AND collection:ciareadingroom", "rows": 0, "output": "json"}
                 ).json()["response"]["numFound"]
        lines.append(f"Internet Archive mirror of the CIA reading room: {n:,} documents match “{q}”")
    except Exception as e:
        lines.append(f"Internet Archive mirror: {type(e).__name__}: {str(e)[:80]}")
    try:
        r = requests.get("https://www.cia.gov/readingroom/document/06835030", headers=HEADERS, timeout=20)
        title = re.search(r"<title>(.*?)</title>", r.text, re.S)
        lines.append(f"cia.gov document page test: HTTP {r.status_code}, title "
                     f"“{clean(title.group(1))[:70] if title else '?'}” (the front page title means cia.gov links redirect)")
    except Exception as e:
        lines.append(f"cia.gov document page test: {type(e).__name__}")
    return lines


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
    return site_search("theblackvault.com/documentarchive", q, "Black Vault", "FOIA document archive", limit,
                       hint="documentarchive")


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
    return site_search("muckrock.com/foi", q, "MuckRock", "FOIA request", limit, hint="FOIA")


def search_doj_epstein(q, limit=10):
    """DOJ Epstein Library (justice.gov/epstein) via site web search."""
    return site_search("justice.gov/epstein", q, "DOJ Epstein Library", "DOJ release", limit, hint="Epstein")


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
    for attempt in range(2):          # loc.gov is slow now and then; one retry before giving up
        try:
            data = _get("https://www.loc.gov/search/", params={"q": q, "fo": "json", "c": limit}, timeout=15).json()
            break
        except (requests.Timeout, requests.ConnectionError):
            if attempt:
                raise
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


def search_uk_archives(q, limit=10):
    """UK National Archives "Discovery" catalogue API (free, official). Records held at Kew,
    including MI5 (KV), GCHQ (HW), Foreign Office and War Office files. Catalogue entries:
    many link to free digitized copies on the Discovery page."""
    r = _get("https://discovery.nationalarchives.gov.uk/API/search/records",
             params={"sps.searchQuery": q, "sps.recordRepositories": "TNA", "sps.resultsPageSize": limit},
             headers={"Accept": "application/json"}, timeout=20)
    data = r.json()
    records = data.get("records") or data.get("Records") or []
    out = []
    for rec in records:
        rid = rec.get("id") or rec.get("Id") or ""
        ref = rec.get("reference") or rec.get("Reference") or ""
        title = rec.get("title") or rec.get("Title") or rec.get("description") or ref
        desc = rec.get("description") or rec.get("Description") or ""
        dates = rec.get("coveringDates") or rec.get("CoveringDates") or ""
        if not rid:
            continue
        kind = "UK National Archives" + (f" · {ref}" if ref else "")
        if ref.startswith("KV"):
            kind += " (MI5 file)"
        elif ref.startswith("HW"):
            kind += " (GCHQ file)"
        out.append(_res("UK National Archives", title, f"https://discovery.nationalarchives.gov.uk/details/r/{rid}",
                        date=str(dates)[:4], kind=kind, snippet=desc if desc != title else ""))
    return out



# ════════════════════════════════════════════════════════════════════════════
# Corporate secrets — UCSF Industry Documents Library (tobacco, opioids, food,
# chemicals, fossil fuels, pharma). Kept out of the main search on purpose:
# the main search is government records only.
# ════════════════════════════════════════════════════════════════════════════

UCSF_SOLR = "https://metadata.idl.ucsf.edu/solr/ltdl3/query"
UCSF_DOC = "https://www.industrydocuments.ucsf.edu/docs/{id}"


def _ucsf_api(q, limit):
    """UCSF's public Solr metadata service. Field names follow the library's published Data API
    (id, ti = title, dd = document date, industry, collection). Not reachable from the dev sandbox,
    so search_ucsf falls back to web search if this fails or comes back empty."""
    data = _get(UCSF_SOLR, params={"q": q, "rows": limit, "wt": "json"}, timeout=20).json()
    out = []
    for d in data.get("response", {}).get("docs", []):
        doc_id = d.get("id") or d.get("tid")
        if not doc_id:
            continue
        def one(v):
            return (v[0] if isinstance(v, list) and v else v) or ""
        title = clean(str(one(d.get("ti")) or one(d.get("title")) or doc_id))
        date = str(one(d.get("dd")) or one(d.get("date")))[:4]
        ind = str(one(d.get("industry"))).title()
        coll = str(one(d.get("collection")) or one(d.get("collectionname")))
        kind = " · ".join(x for x in (f"{ind} industry" if ind else "", coll) if x) or "Industry document"
        out.append(_res("UCSF Industry Documents", title, UCSF_DOC.format(id=doc_id), date=date, kind=kind))
    return out


def search_ucsf(q, limit=15):
    """Internal company documents released through lawsuits, leaks and investigations."""
    try:
        res = _ucsf_api(q, limit)
        if res:
            return res
    except Exception:
        pass
    return site_search("industrydocuments.ucsf.edu", q, "UCSF Industry Documents", "Industry document",
                       limit, url_must_match=r"/docs/", hint="industry documents")


SOURCES = {
    "CIA": search_cia,
    "FBI Vault": search_fbi,
    "GWU Natl Security Archive": search_gwu,
    "DOJ Epstein Library": search_doj_epstein,
    "Internet Archive": search_internet_archive,
    "Library of Congress": search_loc,
    "NASA": search_nasa,
    "Dept of Energy": search_doe,
    "Wikimedia Commons": search_wikimedia,
    "UK National Archives": search_uk_archives,
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


# Sources whose own search matches loosely (any word, or deep in full text). Their results must
# show the search in the title or description: every word, or all but one for 4+ word searches.
LOOSE_SOURCES = {"Library of Congress", "Internet Archive", "Wikimedia Commons", "Dept of Energy",
                 "DOJ Epstein Library", "NASA", "UK National Archives"}


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
    # These catalogs match words buried deep in a book's full text. Hide those unless
    # the search actually appears in the title or description.
    terms = [t.lower() for t in terms_of(q)]
    def relevant(r):
        if r["source"] not in LOOSE_SOURCES or not terms:
            return True
        text = (r["title"] + " " + r["snippet"]).lower()
        need = len(terms) if len(terms) <= 3 else len(terms) - 1   # all words, or all but one for long searches
        return sum(t in text for t in terms) >= need
    hidden = [r for r in results if not relevant(r)]
    results = [r for r in results if relevant(r)]
    for r in hidden:
        if isinstance(status.get(r["source"]), int):
            status[r["source"]] -= 1
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
    pages, note, scanned, followed = [], "", False, False
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
                followed = True
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
            "scanned": scanned and not ocr, "wayback": wayback, "followed": followed}


def _hits_in(text, terms):
    low = text.lower()
    return any(t in low for t in terms)


# Sites with no usable search from a server — opened in the browser instead.
BROWSER_ONLY = [
    ("The Black Vault", "https://www.google.com/search?q=site%3Atheblackvault.com+{q}"),
    ("MuckRock FOIA requests", "https://www.google.com/search?q=site%3Amuckrock.com+{q}"),
    ("NSA declassified releases", "https://www.google.com/search?q=site%3Ansa.gov+declassified+{q}"),
    ("NRO spy satellite files", "https://www.google.com/search?q=site%3Anro.gov+declassified+{q}"),
    ("Wilson Center (Soviet & Cold War files)", "https://www.google.com/search?q=site%3Adigitalarchive.wilsoncenter.org+{q}"),
    ("National Archives (JFK, RFK, MLK)", "https://catalog.archives.gov/search?q={q}"),
    ("Mary Ferrell Foundation", "https://www.google.com/search?q=site%3Amaryferrell.org+{q}"),
    ("WAR.GOV UFO files", "https://www.war.gov/ufo/"),
    ("State Dept FOIA", "https://www.google.com/search?q=site%3Afoia.state.gov+{q}"),
    ("Stasi files (East Germany, mostly in German)", "https://www.google.com/search?q=site%3Astasi-mediathek.de+{q}"),
    ("FilesDropped", "https://www.google.com/search?q=site%3Afilesdropped.com+{q}"),
]

TEST_QUERIES = {"CIA": "MKUltra", "FBI Vault": "Roswell", "GWU Natl Security Archive": "MKUltra",
                "Black Vault": "UFO", "DOJ Epstein Library": "Maxwell", "MuckRock": "CIA", "Internet Archive": "Warren Commission",
                "Library of Congress": "Kennedy", "NASA": "Apollo 11", "Dept of Energy": "Manhattan Project",
                "Wikimedia Commons": "Apollo 11",
                "UK National Archives": "Philby"}


# ════════════════════════════════════════════════════════════════════════════
# Top Secret feed — documents whose own archive listing calls them TOP SECRET
# ════════════════════════════════════════════════════════════════════════════

_TS = re.compile(r"\btop[\s-]*secret\b|\bTS//|\bTS/SCI\b", re.I)


def _real_doe_doc(r):
    """Energy Dept records qualify for the Top Secret panel only if they are old enough to be a
    declassified original (before 2000) and have the document itself to read. That screens out
    modern history articles that merely mention a "top-secret laboratory" (e.g. OSTI 1484619)."""
    year = re.match(r"\d{4}", r.get("date") or "")
    return bool(r.get("file_url")) and bool(year) and int(year.group()) < 2000


def top_secret_pool():
    """Pool of documents marked TOP SECRET, drawn from several archives at once.
    Only government document collections: CIA (via its Internet Archive mirror), GWU National Security
    Archive and the Energy Dept. Internet Archive search and Wikimedia are left out on purpose: their
    "top secret" matches are mostly books, bands and movie posters.
    A document qualifies only if 'TOP SECRET' (or TS//, TS/SCI) is in its own title or description."""
    # The CIA mirror holds ~33,500 documents containing "top secret" (597 with it in the title, Oct 2026).
    # Each refresh draws a random page from both sets, so the panel rotates through the whole collection.
    jobs = {
        "CIA titles": lambda: search_cia('title:"top secret"', limit=40, page=random.randint(1, 14)),
        "CIA": lambda: search_cia('"top secret"', limit=50, page=random.randint(1, 600)),
        "GWU": lambda: search_gwu("top secret", limit=25),
        "Dept of Energy": lambda: search_doe('"top secret"', limit=20),
    }
    pool, seen = [], set()
    with ThreadPoolExecutor(max_workers=len(jobs)) as ex:
        for f in as_completed([ex.submit(fn) for fn in jobs.values()]):
            try:
                for r in f.result():
                    if r["url"] in seen or not _TS.search(r["title"] + " " + r["snippet"]):
                        continue
                    if r["source"] == "Dept of Energy" and not _real_doe_doc(r):
                        continue
                    seen.add(r["url"])
                    if r["source"] == "CIA" and "archive.org/details/" in r["url"]:
                        # picture of the document's first page, made by the Internet Archive
                        r["thumb"] = "https://archive.org/services/img/" + r["url"].rsplit("/", 1)[1]
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

# Where deleted government documents actually live. Scanning a whole domain is too big a job
# for the Wayback Machine to answer quickly, so the dig targets these sections.
VANISHED_SECTIONS = [
    ("cia.gov", "www.cia.gov/library/"),                    # old CIA library, torn down in the 2020 redesign
    ("cia.gov", "www.cia.gov/news-information/"),
    ("nsa.gov", "www.nsa.gov/news-features/"),               # old NSA declassified-documents pages
    ("nsa.gov", "www.nsa.gov/portals/75/documents/"),
    ("fbi.gov", "vault.fbi.gov/"),
    ("dni.gov", "www.dni.gov/files/"),
    ("archives.gov", "www.archives.gov/research/"),
    ("state.gov", "foia.state.gov/"),
    ("defense.gov", "media.defense.gov/"),
    ("aaro.mil", "www.aaro.mil/"),
]
VANISHED_DOMAINS = sorted({d for d, _ in VANISHED_SECTIONS})


def _cdx(section, pattern):
    """Wayback Machine index: saved pages under a site section whose web address matches pattern.
    Retries once if the Wayback Machine says it's busy."""
    params = [("url", section), ("matchType", "prefix"), ("output", "json"),
              ("fl", "original,timestamp,mimetype"), ("filter", "statuscode:200"),
              ("filter", "mimetype:(text/html|application/pdf)"), ("filter", "original:" + pattern),
              ("collapse", "urlkey"), ("limit", "120")]
    for attempt in range(2):
        r = requests.get("https://web.archive.org/cdx/search/cdx", params=params, headers=HEADERS, timeout=30)
        if r.status_code in (429, 503) and attempt == 0:
            _time.sleep(3)
            continue
        r.raise_for_status()
        rows = r.json() if r.text.strip() else []
        return rows[1:] if rows else []
    return []


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
            if orig_path.lower().endswith(".pdf") and "html" in r.headers.get("Content-Type", "").lower():
                return True       # a document that now opens as a web page
            if final_path != orig_path and final_path.count("/") <= orig_path.count("/") - 2:
                return True       # redirected far up the site, e.g. an old document to a front page
            return bool(_NOT_FOUND.search(head))
    except Exception:
        return False


def _title_from_url(url):
    path = urllib.parse.unquote(urllib.parse.urlparse(url).path).rstrip("/")
    name = path.split("/")[-1] or path
    name = re.sub(r"\.(pdf|html?|aspx?|php)$", "", name, flags=re.I)
    name = re.sub(r"[-_+]+", " ", name).strip()
    return name[:1].upper() + name[1:] if name else url


def vanished_pages(q, limit=15):   # not shown in the app (Oct 2026): document addresses are codes, so
    #                                  searching by address misses the best material
    """Government pages whose web address matches the search, that the Wayback Machine saved,
    and that are gone from the live site now. Returns (results, domains_searched_ok)."""
    words = [w for t in terms_of(q) for w in re.findall(r"\w+", t)]
    if not words:
        return [], 0
    pattern = "(?i).*" + "[^/]*".join(re.escape(w) for w in words) + ".*"
    cands, answered = {}, set()
    with ThreadPoolExecutor(max_workers=3) as ex:          # a few at a time: the Wayback Machine rate-limits
        futs = {ex.submit(_cdx, sec, pattern): dom for dom, sec in VANISHED_SECTIONS}
        for f in as_completed(futs):
            try:
                rows = f.result()
                answered.add(futs[f])
            except Exception:
                continue
            for original, ts, mime in rows:
                key = re.sub(r"^https?://(www\.)?|:80(?=/)", "", original).rstrip("/").lower()
                if key not in cands or ts > cands[key][1]:
                    cands[key] = (original.replace(":80/", "/"), ts, mime, futs[f])
    ok = len(answered)
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
