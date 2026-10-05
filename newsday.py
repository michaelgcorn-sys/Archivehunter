"""
"What the public was told": the news on a given day, to set beside the President's Daily Brief.

  wiki_day(d)  - events of that day from Wikipedia's month pages ("October 1974"), no key needed
  nyt_front(d) - New York Times front-page headlines (needs NYT_API_KEY in Secrets, free at developer.nytimes.com)
"""

import os
import re

import requests

MODULE_VERSION = 53   # keep in step with APP_CODE_VERSION in app.py

_UA = {"User-Agent": "ArchiveHunter/1.0 (personal research app for declassified records)"}


def _secret(name):
    try:
        import streamlit as st
        v = st.secrets.get(name)
        if v:
            return str(v).strip()
    except Exception:
        pass
    return os.environ.get(name, "").strip()


def _strip_wiki(t):
    t = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", t, flags=re.S)
    for _ in range(3):
        t = re.sub(r"\{\{[^{}]*\}\}", "", t)
    t = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", t)          # [[a|b]] -> b
    t = re.sub(r"\[https?://\S+ ([^\]]+)\]", r"\1", t)
    t = re.sub(r"'{2,}", "", t)
    t = re.sub(r"<[^>]+>", "", t)
    return re.sub(r"\s+", " ", t).strip(" *:")


def wiki_day(d, limit=4):
    """[event, ...] for date d (a datetime.date), from Wikipedia's 'Month YYYY' page."""
    page = d.strftime("%B_%Y")
    r = requests.get("https://en.wikipedia.org/w/api.php", headers=_UA, timeout=20,
                     params={"action": "parse", "page": page, "prop": "wikitext", "format": "json",
                             "formatversion": 2, "redirects": 1})
    text = r.json().get("parse", {}).get("wikitext", "")
    if not text:
        return []
    day = f"{d.strftime('%B')} {d.day}, {d.year}"
    m = re.search(r"^=+\s*\[*" + re.escape(day) + r".*?=+\s*$", text, re.M)
    if not m:
        return []
    nxt = re.search(r"^=+[^=\n]+=+\s*$", text[m.end():], re.M)
    section = text[m.end(): m.end() + nxt.start()] if nxt else text[m.end():]
    events = []
    for line in section.splitlines():
        if line.startswith("*") and not line.startswith("**"):
            e = _strip_wiki(line)
            if len(e) > 25 and not e.lower().startswith(("born", "died")):
                events.append(e if len(e) <= 220 else e[:220].rsplit(" ", 1)[0] + "…")
        if len(events) >= limit:
            break
    return events


def nyt_available():
    return bool(_secret("NYT_API_KEY"))


def nyt_front(d, limit=5):
    """[(headline, url), ...] from page 1 of the New York Times on date d."""
    ymd = d.strftime("%Y%m%d")
    r = requests.get("https://api.nytimes.com/svc/search/v2/articlesearch.json", timeout=20,
                     params={"begin_date": ymd, "end_date": ymd, "fq": 'print_page:1', "sort": "relevance",
                             "api-key": _secret("NYT_API_KEY")})
    r.raise_for_status()
    docs = (r.json().get("response") or {}).get("docs") or []
    out = []
    for doc in docs:
        h = ((doc.get("headline") or {}).get("main") or "").strip()
        if h and h.lower() not in {x[0].lower() for x in out}:
            out.append((h, doc.get("web_url", "")))
        if len(out) >= limit:
            break
    return out
