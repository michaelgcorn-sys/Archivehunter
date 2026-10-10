"""
"What the public was told": the news on a given day, to set beside the President's Daily Brief.

  wiki_day(d)  - events of that day from Wikipedia's month pages ("October 1974"), no key needed
  nyt_front(d) - New York Times front-page headlines (needs NYT_API_KEY in Secrets, free at developer.nytimes.com)
"""

import os
import re

import requests

MODULE_VERSION = 63   # keep in step with APP_CODE_VERSION in app.py

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


# ── Topic-matched public record ─────────────────────────────────────────────
# Words the news uses for each country (names, adjectives, capitals, leaders' governments)
ALIASES = {
    "USSR": ["Soviet", "USSR", "Moscow", "Kremlin", "Brezhnev", "Khrushchev", "Kosygin"],
    "Soviet Union": ["Soviet", "USSR", "Moscow", "Kremlin", "Brezhnev", "Khrushchev", "Kosygin"],
    "China": ["China", "Chinese", "Peking", "Beijing", "Mao"], "Cuba": ["Cuba", "Cuban", "Havana", "Castro"],
    "Vietnam": ["Vietnam", "Vietnamese", "Saigon", "Hanoi", "Viet Cong"],
    "North Vietnam": ["North Vietnam", "Hanoi", "Vietnam"], "South Vietnam": ["South Vietnam", "Saigon", "Vietnam"],
    "Italy": ["Italy", "Italian", "Rome"], "Portugal": ["Portugal", "Portuguese", "Lisbon"],
    "Cyprus": ["Cyprus", "Cypriot", "Nicosia"], "Greece": ["Greece", "Greek", "Athens"], "Turkey": ["Turkey", "Turkish", "Ankara"],
    "Israel": ["Israel", "Israeli"], "Egypt": ["Egypt", "Egyptian", "Cairo", "Sadat", "Nasser"],
    "Syria": ["Syria", "Syrian", "Damascus"], "Lebanon": ["Lebanon", "Lebanese", "Beirut"], "Jordan": ["Jordanian", "Amman", "King Hussein"],
    "Iran": ["Iran", "Iranian", "Tehran", "Shah"], "Iraq": ["Iraq", "Iraqi", "Baghdad"],
    "Saudi Arabia": ["Saudi"], "Libya": ["Libya", "Libyan", "Qaddafi", "Gaddafi"],
    "West Germany": ["West Germany", "West German", "Bonn", "Germany"], "East Germany": ["East Germany", "East German"],
    "Berlin": ["Berlin"], "France": ["France", "French", "Paris"], "United Kingdom": ["Britain", "British", "London", "United Kingdom"],
    "Britain": ["Britain", "British", "London"], "Japan": ["Japan", "Japanese", "Tokyo"],
    "North Korea": ["North Korea", "Pyongyang"], "South Korea": ["South Korea", "Seoul"], "Korea": ["Korea", "Korean"],
    "India": ["India", "Indian", "New Delhi", "Gandhi"], "Pakistan": ["Pakistan", "Pakistani"],
    "Chile": ["Chile", "Chilean", "Santiago", "Allende", "Pinochet"], "Argentina": ["Argentina", "Argentine", "Buenos Aires", "Perón", "Peron"],
    "Brazil": ["Brazil", "Brazilian"], "Mexico": ["Mexico", "Mexican"], "Panama": ["Panama", "Panamanian"],
    "Poland": ["Poland", "Polish", "Warsaw"], "Czechoslovakia": ["Czechoslovakia", "Czech", "Prague"],
    "Hungary": ["Hungary", "Hungarian", "Budapest"], "Yugoslavia": ["Yugoslavia", "Yugoslav", "Belgrade", "Tito"],
    "Romania": ["Romania", "Romanian", "Bucharest"], "Laos": ["Laos", "Laotian"], "Cambodia": ["Cambodia", "Cambodian", "Phnom Penh"],
    "Thailand": ["Thailand", "Thai", "Bangkok"], "Indonesia": ["Indonesia", "Indonesian", "Jakarta", "Sukarno", "Suharto"],
    "Philippines": ["Philippines", "Philippine", "Manila", "Marcos"], "Ethiopia": ["Ethiopia", "Ethiopian", "Haile Selassie"],
    "Angola": ["Angola", "Angolan"], "Rhodesia": ["Rhodesia", "Rhodesian"], "South Africa": ["South Africa", "South African"],
    "Spain": ["Spain", "Spanish", "Madrid", "Franco"], "Afghanistan": ["Afghanistan", "Afghan", "Kabul"],
    "Middle East": ["Middle East", "Israel", "Egypt", "Syria", "Arab"], "NATO": ["NATO"],
}


def _month_wikitext(year, month):
    import datetime
    page = datetime.date(year, month, 1).strftime("%B_%Y")
    r = requests.get("https://en.wikipedia.org/w/api.php", headers=_UA, timeout=20,
                     params={"action": "parse", "page": page, "prop": "wikitext", "format": "json",
                             "formatversion": 2, "redirects": 1})
    return r.json().get("parse", {}).get("wikitext", "")


def month_events(year, month):
    """[(date, event text), ...] for every day of a month, from Wikipedia's 'Month YYYY' page."""
    import datetime
    text = _month_wikitext(year, month)
    out = []
    mname = datetime.date(year, month, 1).strftime("%B")
    heads = list(re.finditer(r"^=+\s*\[*" + mname + r" (\d{1,2}), " + str(year) + r".*?=+\s*$", text, re.M))
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        day = datetime.date(year, month, int(h.group(1)))
        for line in text[h.end():end].splitlines():
            if line.startswith("*") and not line.startswith("**"):
                e = _strip_wiki(line)
                if len(e) > 25 and not e.lower().startswith(("born", "died")):
                    out.append((day, e))
    return out


def public_on_topics(d, topics, window=7, per_topic=1):
    """{topic: [(date, event), ...]} public-record events about each topic within `window` days of d."""
    import datetime
    events = []
    months = {(d.year, d.month)}
    for delta in (-window, window):
        x = d + datetime.timedelta(days=delta)
        months.add((x.year, x.month))
    for y, m in sorted(months):
        try:
            events += month_events(y, m)
        except Exception:
            continue
    out = {}
    for t in topics:
        words = ALIASES.get(t, [t])
        rx = re.compile(r"\b(" + "|".join(re.escape(w) for w in words) + r")", re.I)
        hits = [(day, e) for day, e in events if abs((day - d).days) <= window and rx.search(e)]
        hits.sort(key=lambda x: (abs((x[0] - d).days), x[0] > d))       # closest first, earlier on ties
        out[t] = [(day, e if len(e) <= 230 else e[:230].rsplit(" ", 1)[0] + "…") for day, e in hits[:per_topic]]
    return out


def nyt_on_topic(d, topic, window=3, limit=2):
    """[(headline, url, date), ...] New York Times stories about a topic around date d (needs NYT_API_KEY)."""
    import datetime
    a = (d - datetime.timedelta(days=window)).strftime("%Y%m%d")
    b = (d + datetime.timedelta(days=window)).strftime("%Y%m%d")
    r = requests.get("https://api.nytimes.com/svc/search/v2/articlesearch.json", timeout=20,
                     params={"q": topic, "begin_date": a, "end_date": b, "sort": "relevance",
                             "api-key": _secret("NYT_API_KEY")})
    r.raise_for_status()
    out = []
    for doc in ((r.json().get("response") or {}).get("docs") or [])[:limit]:
        h = ((doc.get("headline") or {}).get("main") or "").strip()
        if h:
            out.append((h, doc.get("web_url", ""), (doc.get("pub_date") or "")[:10]))
    return out
