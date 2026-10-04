"""
Exhibit A — Archive Hunter (web version)
Run locally:  streamlit run app.py
"""

import html
import random
import re
import urllib.parse

import streamlit as st

import importlib

import sources

APP_CODE_VERSION = 43
if getattr(sources, "CODE_VERSION", None) != APP_CODE_VERSION:
    # Streamlit Cloud can keep an old copy of sources.py in memory after an update.
    sources = importlib.reload(sources)
import catalog
if getattr(catalog, "CATALOG_VERSION", None) != APP_CODE_VERSION:
    catalog = importlib.reload(catalog)   # same stale-module problem for catalog.py

from sources import (BROWSER_ONLY, SOURCES, TEST_QUERIES, diagnose_cia, find_passages, saved_copy_url,
                     pdb_on_this_day, search_all, search_cia, search_pdb, search_ucsf, top_secret_pool)
from catalog import ANCIENT, CATEGORIES, CORPORATE, PICKS, TEASERS, met_gallery, met_image

st.set_page_config(page_title="Archive Hunter", page_icon="🗂️", layout="centered")

st.markdown("""
<style>
.block-container{padding-top:5rem;max-width:760px}
.eyebrow{font:700 .72rem 'Courier New',monospace;letter-spacing:.18em;color:#c4544a;text-transform:uppercase}
.brand-link,.brand-link:hover{text-decoration:none!important}
.brand{font:700 2rem/1.1 'Courier New',monospace;color:#c8a96e;margin:.1rem 0 .2rem}
.src{font:700 .7rem 'Courier New',monospace;letter-spacing:.08em;text-transform:uppercase;color:#c8a96e}
.meta{font-size:.8rem;opacity:.65}
.res-title a{font-weight:600;font-size:1.02rem;text-decoration:none}
.snip{font-size:.88rem;opacity:.8;margin-top:.15rem}
.passage{font-size:.9rem;line-height:1.5;border-left:3px solid #c8a96e;padding:.35rem .7rem;margin:.45rem 0;
         background:rgba(200,169,110,.07);border-radius:0 4px 4px 0}
.passage mark{background:#c8a96e;color:#111;padding:0 2px;border-radius:2px}
.pg{font:700 .7rem 'Courier New',monospace;opacity:.6}
.ver{font:.72rem 'Courier New',monospace;opacity:.5;margin-bottom:.6rem}
.ts-head{display:flex;align-items:center;gap:.6rem;margin:.2rem 0 .4rem}
.ts-head b{font:700 .72rem 'Courier New',monospace;letter-spacing:.2em;color:#c4544a;white-space:nowrap}
.ts-head span{font-size:.75rem;opacity:.55}
.ts-strip{display:flex;gap:10px;overflow-x:auto;scroll-snap-type:x mandatory;padding:2px 2px 10px;
          -webkit-overflow-scrolling:touch;scrollbar-width:thin}
.ts-card{flex:0 0 190px;scroll-snap-align:start;position:relative;display:flex;flex-direction:column;
         background:#1b1a15;border:1px solid #3a3528;border-radius:6px;overflow:hidden;
         text-decoration:none!important;color:#ebe8de!important}
.ts-card:hover{border-color:#c8a96e}
.ts-img{height:120px;background:#2a2720 center/cover no-repeat;position:relative}
.ts-img.folder{background:linear-gradient(135deg,#3b3324,#5a4b2e);display:flex;align-items:center;
               justify-content:center;font:700 .65rem 'Courier New',monospace;letter-spacing:.2em;color:#d9c79c}
.ts-stamp{position:absolute;top:10px;right:-6px;transform:rotate(8deg);border:2px solid #d0473b;color:#e2564a;
          background:rgba(20,10,8,.75);font:700 .62rem 'Courier New',monospace;letter-spacing:.14em;padding:2px 7px}
.ts-body{padding:.5rem .6rem .6rem;display:flex;flex-direction:column;gap:.2rem}
.ts-src{font:700 .6rem 'Courier New',monospace;letter-spacing:.1em;text-transform:uppercase;color:#c8a96e}
.ts-title{font-size:.8rem;line-height:1.3;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden}
.st-key-popular{border:1.5px solid #c4544a;border-radius:8px;padding:.6rem .75rem .75rem;margin:.4rem 0 .2rem;gap:.4rem}
.pop-label{font-size:1.17rem;font-weight:700;color:#c4544a;line-height:1.3;padding:.1rem 0 .5rem;display:block}
.st-key-popular [data-testid="stMarkdownContainer"]{overflow:visible;margin-bottom:0}
.st-key-popular [data-testid="stElementContainer"]{height:auto!important}
.st-key-qbox div:has(> input),.st-key-qbox [data-baseweb="input"]{border:2px solid #c8a96e!important;border-radius:10px!important;background:#1d1a14!important;box-shadow:0 0 0 3px rgba(200,169,110,.12)}
.st-key-qbox div:has(> input):focus-within,.st-key-qbox [data-baseweb="input"]:focus-within{box-shadow:0 0 0 4px rgba(200,169,110,.35)}
.st-key-qbox [data-baseweb="base-input"]{background:transparent!important}
.st-key-qbox input{font-size:1.1rem!important;height:3.2rem;padding-left:2.7rem!important;color:#f1e6cc!important;background-color:transparent!important;
 background:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='22' height='22' viewBox='0 0 24 24' fill='none' stroke='%23c8a96e' stroke-width='2.5' stroke-linecap='round'%3E%3Ccircle cx='10.5' cy='10.5' r='6.5'/%3E%3Cpath d='M15.5 15.5 21 21'/%3E%3C/svg%3E") no-repeat .8rem center!important}
.st-key-qbox input::placeholder{color:#b9ab8c!important;opacity:1}
.qtip{font-size:.82rem;color:#b9ab8c;margin:-.35rem 0 .1rem .2rem}
.which{font-size:1.17rem;line-height:1.4;opacity:.9;margin:.5rem 0 .4rem}
.links{display:flex;flex-wrap:wrap;gap:.45rem;margin:.35rem 0 .1rem}
.links a{font-size:.82rem;font-weight:600;text-decoration:none;color:#c8a96e;border:1px solid #3a3528;border-radius:999px;padding:.22rem .7rem;background:#171714}
.links a:hover{border-color:#c8a96e}
.intro{font-size:.88rem;opacity:.75;margin:.2rem 0 .6rem}
[class*="-tile"] button{height:118px;align-items:flex-start;justify-content:flex-start;text-align:left;
  padding:.7rem .75rem;background:linear-gradient(160deg,#1f1c15,#14130f);border:1px solid #3a3528;border-radius:8px}
[class*="-tile"] button:hover{border-color:#c8a96e;background:linear-gradient(160deg,#29241a,#16140f)}
[class*="-tile"] button *{white-space:normal!important;overflow:visible!important;text-overflow:clip!important}
[class*="-tile"] button p{font-size:.76rem;line-height:1.3;opacity:.82;margin:0;text-align:left}
[class*="-tile"] button p strong{display:block;font-size:.92rem;line-height:1.2;color:#e8d3a0;opacity:1;margin:.3rem 0 .25rem}
[class*="-tilesel-"] button{border-color:#c8a96e;box-shadow:0 0 0 1px #c8a96e inset;background:linear-gradient(160deg,#3a3020,#1c1810)}
[class*="-tile-anc"] button{background:linear-gradient(160deg,#2a2013,#17120b);border-color:#6b5230}
.corp-card{background:#17181b;border:1px solid #34373d;border-left:3px solid #8a9bb0;border-radius:6px;padding:.85rem 1rem;margin:.6rem 0 .1rem}
.corp-title{font-weight:700;font-size:1.05rem;color:#dfe6ee;margin-bottom:.25rem}
.corp-what{font-size:.88rem;opacity:.85;margin-bottom:.35rem}
.corp-src{font-size:.8rem;font-weight:600;color:#9fb3c8!important;text-decoration:none}
[class*="st-key-corpgo"] button p{color:#c8a96e;font-weight:600;font-size:.85rem}
[class*="-tile-corp"] button{background:linear-gradient(160deg,#1a1d22,#121417);border-color:#3c4450}
.topic-head{font:700 1.35rem 'Courier New',monospace;color:#c8a96e;margin:1rem 0 .1rem}
.sect{font:700 .7rem 'Courier New',monospace;letter-spacing:.16em;color:#c8a96e;margin:1rem 0 .3rem}
.anc-intro{font-family:Georgia,'Times New Roman',serif;font-size:1rem;line-height:1.55;color:#e6d6b8;
           border-left:3px solid #b98a4e;padding:.2rem .9rem;margin:.3rem 0 1rem}
.anc-card{background:#1c1710;border:1px solid #4a3a22;border-radius:6px;padding:1rem 1.1rem;margin:0 0 .9rem}
.anc-img{width:100%;max-height:340px;object-fit:contain;background:#120f0a;border-radius:4px;margin-bottom:.7rem}
.anc-where{font:700 .66rem 'Courier New',monospace;letter-spacing:.12em;text-transform:uppercase;color:#b98a4e}
.anc-title{font-family:Georgia,'Times New Roman',serif;font-size:1.3rem;color:#ecd9b0;margin:.15rem 0 .35rem}
.anc-what{font-size:.9rem;opacity:.85}
.anc-quote{font-family:Georgia,'Times New Roman',serif;font-style:italic;font-size:1rem;line-height:1.55;
           color:#e6d6b8;background:rgba(185,138,78,.08);border-left:3px solid #b98a4e;padding:.5rem .8rem;margin:.6rem 0}
.anc-src{font-size:.8rem;font-weight:600;color:#b98a4e!important;text-decoration:none}
.met-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;margin-top:.6rem}
.met-tile{display:flex;flex-direction:column;background:#1c1710;border:1px solid #4a3a22;border-radius:6px;
          overflow:hidden;text-decoration:none!important;color:#e6d6b8!important}
.met-tile img{width:100%;height:140px;object-fit:cover;background:#120f0a}
.met-tile span{font-size:.72rem;padding:.4rem .5rem;line-height:1.3}
</style>
<div class="eyebrow">Exhibit A · Declassified</div>
<a class="brand-link" href="./" target="_self"><div class="brand">Archive Hunter</div></a>
<div class="ver">Version 43 · updated Oct 4, 2026</div>
""", unsafe_allow_html=True)

ALL = list(SOURCES)
ss = st.session_state
ss.setdefault("results", [])
ss.setdefault("status", {})
ss.setdefault("open_doc", None)
ss.setdefault("ocr_doc", None)
ss.setdefault("query", "")


@st.cache_data(ttl=3600, show_spinner=False)    # new random batch every hour
def cached_pool(v=APP_CODE_VERSION):    # version in the key: an update throws out old answers
    return top_secret_pool()


@st.fragment(run_every="30s")
def top_secret_strip():
    pool = cached_pool(APP_CODE_VERSION)
    if not pool:
        return
    picks = random.sample(pool, min(10, len(pool)))
    cards = []
    for r in picks:
        if r.get("thumb"):
            img = f'<div class="ts-img" style="background-image:url(\'{html.escape(r["thumb"])}\')">'
        else:
            img = f'<div class="ts-img folder">{html.escape(r["source"].upper())}'
        year = f" · {r['date']}" if r["date"] else ""
        cards.append(
            f'<a class="ts-card" href="{html.escape(r["url"])}" target="_blank">{img}'
            f'<span class="ts-stamp">TOP SECRET</span></div><div class="ts-body">'
            f'<span class="ts-src">{html.escape(r["source"])}{year}</span>'
            f'<span class="ts-title">{html.escape(r["title"])}</span></div></a>')
    st.markdown(
        f'<div class="ts-head"><b>● TOP SECRET</b><span>{len(pool)} document{"" if len(pool) == 1 else "s"} marked Top Secret · '
        f'new picks every 30 seconds · swipe and tap to open</span></div>'
        f'<div class="ts-strip">{"".join(cards)}</div>', unsafe_allow_html=True)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_search(q, names, v=APP_CODE_VERSION):
    return search_all(q, list(names))


@st.cache_data(ttl=6 * 3600, show_spinner=False, max_entries=60)
def cached_passages(url, q, ocr=False, v=APP_CODE_VERSION):
    return find_passages(url, q, ocr=ocr)


with st.spinner("Pulling Top Secret documents from the archives…"):
    top_secret_strip()


@st.cache_data(ttl=6 * 3600, show_spinner=False, max_entries=40)
def cached_cia(q, v=APP_CODE_VERSION):
    return search_cia(q, limit=6)


@st.cache_data(ttl=6 * 3600, show_spinner=False, max_entries=80)
def cached_pdb(day, v=APP_CODE_VERSION):
    return search_pdb(day)


@st.cache_data(ttl=6 * 3600, show_spinner=False, max_entries=10)
def cached_this_day(month, day, v=APP_CODE_VERSION):
    return pdb_on_this_day(month, day)


@st.cache_data(ttl=3600, show_spinner=False, max_entries=40)
def cached_corp(q, v=APP_CODE_VERSION):
    return search_ucsf(q, limit=15)


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def cached_met_image(object_id, v=APP_CODE_VERSION):
    return met_image(object_id)


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def cached_met_gallery(v=APP_CODE_VERSION):
    return met_gallery()


def render_result(r, uid, saved_copy=True, query=None):
    """One result card: title, source, buttons, and the "find my words" passages."""
    key = r["url"]
    q_used = query or ss.query
    with st.container(border=True):
        st.markdown(
            f'<div class="src">{html.escape(r["source"])}</div>'
            f'<div class="res-title"><a href="{html.escape(r["url"])}" target="_blank">{html.escape(r["title"])}</a></div>'
            f'<div class="meta">{html.escape(" · ".join(x for x in (r["kind"], r["date"][:4]) if x))}</div>'
            + (f'<div class="snip">{html.escape(r["snippet"])}</div>' if r["snippet"] else ""),
            unsafe_allow_html=True)
        links = [f'<a href="{html.escape(r["url"])}" target="_blank">Open ↗</a>']
        if r["file_url"]:
            links.append(f'<a href="{html.escape(r["file_url"])}" target="_blank">Download ⬇</a>')
        if saved_copy:
            links.append(f'<a href="{html.escape(saved_copy_url(r["url"]))}" target="_blank" '
                         f'title="The Wayback Machine\'s most recent saved copy of this page">🕰 Saved copy</a>')
        st.markdown(f'<div class="links">{" ".join(links)}</div>', unsafe_allow_html=True)
        if r["doc_url"]:
            if st.button("🔎 Find my words inside", key=f"f{uid}{key}", use_container_width=True):
                ss.open_doc = None if ss.open_doc == key else key
                ss.ocr_doc = None

        if ss.open_doc != key:
            return
        with st.spinner("Reading the document… big PDFs take up to a minute"):
            try:
                p = cached_passages(r["doc_url"], q_used, False, APP_CODE_VERSION)
            except Exception as e:
                p = None
                st.warning(f"Couldn't read this one, and the Wayback Machine has no saved copy "
                           f"({type(e).__name__}). Tap Open to try it on the site.")
        if p and p.get("wayback"):
            wb = p["wayback"]
            st.info(f"🕰 The original page is gone. These results come from a saved copy "
                    f"from {wb['date']} (Wayback Machine).")
            st.link_button("Open saved copy", wb["view"])
        if p and p.get("scanned"):
            st.warning(p["note"])
            if st.button("📷 Read the scanned pages (takes 1–2 minutes)", key=f"o{uid}{key}",
                         use_container_width=True):
                ss.ocr_doc = key
            if ss.ocr_doc == key:
                with st.spinner("Reading scanned pages with character recognition…"):
                    try:
                        p = cached_passages(r["doc_url"], q_used, True, APP_CODE_VERSION)
                    except Exception as e:
                        st.warning(f"Character recognition failed ({type(e).__name__}).")
        if p and not p.get("scanned"):
            where = f"{p['pages']} pages" if p["pages"] else (
                "the full document" if r["doc_url"].endswith(".txt") else "the page")
            if p["hits"]:
                st.success(f"{len(p['hits'])} passage(s) mention your search · read {where}")
                if p["note"]:
                    st.caption(p["note"])
            elif p["note"]:
                st.warning(p["note"] + " Your words didn't turn up in what was read.")
            else:
                st.info(f"Read {where} — your words don't appear in the text. "
                        "The search may have matched the title or catalog entry instead.")
            for pno, text, marks in p["hits"]:
                out, last = [], 0
                for a, b in marks:
                    out += [html.escape(text[last:a]), "<mark>", html.escape(text[a:b]), "</mark>"]
                    last = b
                out.append(html.escape(text[last:]))
                tag = f'<div class="pg">PAGE {pno}</div>' if pno else ""
                st.markdown(f'<div class="passage">{tag}…{"".join(out)}…</div>', unsafe_allow_html=True)
            if p.get("followed"):
                st.link_button("Open the PDF these came from", p["read_url"])



TAB_SEARCH, TAB_EXPLORE, TAB_ANCIENT, TAB_CORP = "🔎  Search", "🗂  Explore", "🏺  Ancient", "🏢  Corporate"
TOPIC_LABELS = [f"{icon} {name}" for name, icon, *_ in CATEGORIES]
ss.setdefault("topic", TOPIC_LABELS[0])


def _open_topic(label):
    ss.topic = label
    ss.main_tabs = TAB_EXPLORE


def _open_ancient():
    ss.main_tabs = TAB_ANCIENT


def _open_corp():
    ss.main_tabs = TAB_CORP


def topic_tiles(prefix, with_ancient=False):
    """Deep-dive tiles. Tapping one opens that topic in the Explore tab."""
    with st.container(horizontal=True, wrap=True, gap="small", key=f"{prefix}-tiles"):
        for i, (name, icon, *_rest) in enumerate(CATEGORIES):
            label = f"{icon} {name}"
            sel = "sel" if (prefix == "ex" and ss.topic == label) else ""
            st.button(f"{icon}  **{name}**\n\n{TEASERS[name]}", key=f"{prefix}-tile{sel}-{i}",
                      on_click=_open_topic, args=(label,), width=164, wrap=True)
        if with_ancient:
            st.button("🏺  **Ancient Intelligence**\n\nPlots, spies and curses, 3,000 years old", key=f"{prefix}-tile-anc",
                      on_click=_open_ancient, width=164, wrap=True)
            st.button("🏢  **Corporate Secrets**\n\nTobacco, opioids, Enron: the memos they hid", key=f"{prefix}-tile-corp",
                      on_click=_open_corp, width=164, wrap=True)


def _pdb_random():
    from datetime import date, timedelta
    a, b = date.fromisoformat(sources.PDB_FIRST), date.fromisoformat(sources.PDB_LAST)
    ss.pdb_day = a + timedelta(days=random.randint(0, (b - a).days))


def pdb_block():
    """Pick a date, read the President's Daily Brief from that morning."""
    from datetime import date
    st.markdown('<div class="intro">The CIA’s top-secret morning briefing for the president. About 4,000 '
                'have been declassified, from <b>June 1961 to January 1977</b> (Kennedy, Johnson, Nixon, '
                'Ford). Pick a date — your birthday, the day Nixon resigned (Aug 9, 1974), the fall of Saigon '
                '(Apr 30, 1975) — and read what the president was told. Kennedy’s were called the '
                '“President’s Intelligence Checklist” and are fewer.</div>',
                unsafe_allow_html=True)
    ss.setdefault("pdb_day", date(1965, 5, 15))
    c1, c2 = st.columns([3, 2], vertical_alignment="bottom")
    c1.date_input("Date", key="pdb_day", min_value=date.fromisoformat(sources.PDB_FIRST),
                  max_value=date.fromisoformat(sources.PDB_LAST), format="MM/DD/YYYY")
    c2.button("🎲 Random day", on_click=_pdb_random, use_container_width=True)
    day = ss.pdb_day.isoformat()
    with st.spinner("Pulling the briefs…"):
        try:
            briefs = cached_pdb(day, APP_CODE_VERSION)
        except Exception:
            briefs = None
    if briefs is None:
        st.caption("The CIA files didn't answer just now. Try again in a minute.")
        return
    if not briefs:
        st.info("No brief was released for the days around that date. Try another date, or 🎲 Random day.")
        return
    st.markdown(f'<div class="sect">BRIEFS CLOSEST TO {ss.pdb_day.strftime("%B %-d, %Y").upper()} · {len(briefs)}</div>',
                unsafe_allow_html=True)
    for i, r in enumerate(briefs):
        render_result(r, f"pdb{i}", query=None)


def _brief_date(r):
    """Full date from a brief's title ("... DAILY BRIEF 4 OCTOBER 1966"), or None."""
    from datetime import datetime
    m = re.search(r"(\d{1,2})\s+([A-Z]{3})[A-Z]*\.?,?\s+(\d{4})", r["title"].upper())
    try:
        return datetime.strptime(f"{m[1]} {m[2]} {m[3]}", "%d %b %Y").date() if m else None
    except ValueError:
        return None


def _open_pdb_at(d):
    ss.topic = TOPIC_LABELS[[c[0] for c in CATEGORIES].index("Presidential Daily Briefs")]
    if d:
        ss.pdb_day = d
    ss.main_tabs = TAB_EXPLORE


def on_this_day_card():
    """Home-page card: the President's Daily Brief from today's date in a past year."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    today = datetime.now(ZoneInfo("America/New_York")).date()
    try:
        briefs = cached_this_day(today.month, today.day, APP_CODE_VERSION)
    except Exception:
        return
    if not briefs:
        return
    r = random.Random(today.isoformat()).choice(briefs)     # same pick all day, new one tomorrow
    d = _brief_date(r)
    yr = d.year if d else (r["date"] or "")
    st.markdown(f'<div class="sect">📜 ON THIS DAY · {today.strftime("%B %-d").upper()}, {yr}</div>'
                f'<div class="intro">What the CIA told the president that morning.</div>', unsafe_allow_html=True)
    render_result(r, "otd", query=None)
    st.button("📜 Read briefs from other dates", key="otd-more", on_click=_open_pdb_at, args=(d,),
              use_container_width=True)


tab_search, tab_explore, tab_ancient, tab_corp = st.tabs([TAB_SEARCH, TAB_EXPLORE, TAB_ANCIENT, TAB_CORP], key="main_tabs", on_change="rerun")

with tab_search:
    # ── Search box ───────────────────────────────────────────────────────────────
    QUICK = ["MKUltra", "JFK Oswald Mexico City", "Roswell", "Epstein", "Area 51", "Stargate",
             "COINTELPRO", "Bay of Pigs", "Operation Northwoods"]

    def _use_quick():
        """A quick button fills the search box and runs it, then un-highlights itself."""
        if ss.get("quick"):
            ss.qbox = ss.quick
            ss.run_quick = True
        ss.quick = None


    def _go_home():
        """Clear the search and bring back the front page (tiles and all)."""
        for k in ("results", "status"):
            ss[k] = [] if k == "results" else {}
        ss.query, ss.qbox, ss.open_doc, ss.ocr_doc = "", "", None, None
        ss.main_tabs = TAB_SEARCH

    ss.setdefault("qbox", "")
    with st.form("search", border=False):
        st.text_input("Search", key="qbox", placeholder='Search: name, program or event…',
                      label_visibility="collapsed")
        st.markdown('<div class="qtip">💡 Tip: use "quotes" for an exact phrase</div>', unsafe_allow_html=True)
        go = st.form_submit_button("Search all archives", type="primary", use_container_width=True)

    with st.container(key="popular"):
        st.markdown('<div class="pop-label">Popular searches</div>', unsafe_allow_html=True)
        st.pills("Try", QUICK, key="quick", on_change=_use_quick, label_visibility="collapsed")
    q = ss.qbox
    if ss.pop("run_quick", False):
        go = True

    ss.setdefault("chosen", ALL)
    st.markdown(f'<div class="which"><b>Searching {len(ss.chosen)} archives:</b> {html.escape(" · ".join(ss.chosen))}</div>',
                unsafe_allow_html=True)
    with st.expander("Turn archives on or off"):
        chosen = st.pills("Archives", ALL, selection_mode="multi", default=ss.chosen, label_visibility="collapsed")
        if chosen is not None and list(chosen) != list(ss.chosen):
            ss.chosen = list(chosen)
            st.rerun()
    chosen = ss.chosen

    if go and q.strip():
        ss.query = q.strip()
        ss.open_doc = None
        with st.spinner(f"Searching {len(chosen)} archives at once…"):
            ss.results, ss.status = cached_search(ss.query, tuple(chosen), APP_CODE_VERSION)

    # ── Deep dives: tiles on the empty front page ──────────────────────────────
    if not ss.status:
        on_this_day_card()
        st.markdown('<div class="sect">DEEP DIVES · tap a topic</div>', unsafe_allow_html=True)
        topic_tiles("home", with_ancient=True)

    # ── Results ──────────────────────────────────────────────────────────────────
    results, status = ss.results, ss.status
    if status:
        st.button("🏠  Back to home", key="home-top", on_click=_go_home, use_container_width=True)
        ok = [f"{n} {c}" for n, c in status.items() if isinstance(c, int)]
        bad = [n for n, c in status.items() if not isinstance(c, int)]
        st.caption(f"**{len(results)} results** for “{ss.query}” · " + " · ".join(ok)
                   + (f"  \n⚠️ No answer from: {', '.join(bad)}" if bad else ""))

        have = sorted({r["source"] for r in results})
        only = st.pills("Show", ["All"] + have, default="All", label_visibility="collapsed") or "All"
        shown = [r for r in results if only == "All" or r["source"] == only]

        if not shown:
            st.info("Nothing came back. Try fewer or different words, or one of the browser links below.")

        for i, r in enumerate(shown[:80]):
            render_result(r, f"r{i}")
        st.button("🏠  Back to home", key="home-bottom", on_click=_go_home, use_container_width=True)

    # ── Sites that only work in the browser ──────────────────────────────────────
    st.divider()
    term = urllib.parse.quote(ss.query or "")
    if term:
        st.markdown(f"**Not in the main search** · these archives only work on their own websites. "
                    f"Tap one to open it with “{html.escape(ss.query)}” filled in (opens in a new tab).")
    else:
        st.markdown("**Not in the main search** · these archives only work on their own websites. "
                    "Tap one to visit it (opens in a new tab). Search first and they open with your words filled in.")
    c = st.columns(2)
    links = [b for b in BROWSER_ONLY if not (b[0].startswith("National Archives") and "National Archives" in SOURCES)]
    for j, (name, tpl, home) in enumerate(links):
        c[j % 2].link_button(name, tpl.replace("{q}", term) if term else home, use_container_width=True)


# ── Explore: browse by topic ──────────────────────────────────────────────────
with tab_explore:
    st.markdown('<div class="intro">Not sure what to search for? Pick a topic. You get hand-picked '
                'documents (checked against the source) plus fresh finds from the CIA files.</div>',
                unsafe_allow_html=True)
    topic_tiles("ex")
    topic = ss.topic if ss.topic in TOPIC_LABELS else TOPIC_LABELS[0]
    if topic:
        name, icon, cia_q, main_q, pick_ids = CATEGORIES[TOPIC_LABELS.index(topic)]
        st.markdown(f'<div class="topic-head">{html.escape(icon)} {html.escape(name)}</div>'
                    f'<div class="intro">{html.escape(TEASERS[name])}</div>', unsafe_allow_html=True)
        if name == "Presidential Daily Briefs":
            pdb_block()
        else:
            picks = [PICKS[p] for p in pick_ids]
            if picks:
                st.markdown('<div class="sect">★ EDITOR\'S PICKS</div>', unsafe_allow_html=True)
                for i, r in enumerate(picks):
                    render_result(r, f"ep{i}", query=main_q)
            st.markdown(f'<div class="sect">FROM THE CIA FILES · “{html.escape(cia_q)}”</div>', unsafe_allow_html=True)
            try:
                live = cached_cia(cia_q, APP_CODE_VERSION)
            except Exception:
                live = []
                st.caption("The CIA files didn't answer just now. Try again in a minute.")
            for i, r in enumerate(live):
                render_result(r, f"ec{i}", query=main_q)
            if st.button(f"Search all {len(ALL)} archives for “{main_q}”", key=f"exall{name}", use_container_width=True):
                ss.explore_all = main_q
            if ss.get("explore_all") == main_q:
                with st.spinner("Searching every archive…"):
                    more, _ = cached_search(main_q, tuple(ALL), APP_CODE_VERSION)
                seen = {r["url"] for r in picks + live}
                more = [r for r in more if r["url"] not in seen]
                st.markdown(f'<div class="sect">MORE FROM ALL ARCHIVES · {len(more)}</div>', unsafe_allow_html=True)
                for i, r in enumerate(more[:40]):
                    render_result(r, f"ea{i}", query=main_q)

# ── Ancient Intelligence: spies and secret reports from the ancient world ─────
with tab_ancient:
    st.markdown('<div class="anc-intro"><b>Long before the CIA</b>, kings ran spies, read intelligence '
                'reports, put plotters on trial and investigated corruption, on clay, papyrus, wood and lead. '
                'These are real ones, and every quote comes from the scholars who published them.</div>', unsafe_allow_html=True)
    for i, item in enumerate(ANCIENT):
        img = None
        if item["met_id"]:
            try:
                img = cached_met_image(item["met_id"], APP_CODE_VERSION)
            except Exception:
                img = None
        quote = (f'<div class="anc-quote">“{html.escape(item["quote"])}”</div>' if item["quote"] else "")
        pic = (f'<img class="anc-img" src="{html.escape(img)}" alt="{html.escape(item["title"])}">' if img else "")
        st.markdown(
            f'<div class="anc-card">{pic}<div class="anc-where">{html.escape(item["where"])}</div>'
            f'<div class="anc-title">{html.escape(item["title"])}</div>'
            f'<div class="anc-what">{html.escape(item["what"])}</div>{quote}'
            f'<a class="anc-src" href="{html.escape(item["url"])}" target="_blank">{html.escape(item["source"])} ↗</a></div>',
            unsafe_allow_html=True)
    if st.button("🏺 Show more ancient tablets from the Met Museum", key="metmore", use_container_width=True):
        ss.met_more = True
    if ss.get("met_more"):
        with st.spinner("Pulling tablets from the Metropolitan Museum…"):
            try:
                gallery = cached_met_gallery(APP_CODE_VERSION)
            except Exception:
                gallery = []
        if gallery:
            tiles = "".join(
                f'<a class="met-tile" href="{html.escape(g["url"])}" target="_blank">'
                f'<img src="{html.escape(g["img"])}" alt=""><span>{html.escape(g["title"])}'
                f'{" · " + html.escape(g["date"]) if g["date"] else ""}</span></a>' for g in gallery)
            st.markdown(f'<div class="met-grid">{tiles}</div>', unsafe_allow_html=True)
            st.caption("Photos: The Metropolitan Museum of Art, public domain.")
        else:
            st.caption("The Met didn't answer just now. Try again in a minute.")


# ── Corporate Secrets: company records pried loose by lawsuits, leaks and investigations ──
def _corp_go(q):
    ss.corp_q = q


with tab_corp:
    st.markdown('<div class="intro"><b>Not every secret is the government\'s.</b> These are companies\' own '
                'internal memos, emails and research, made public through lawsuits, leaks and investigations. '
                'Kept separate from the main search, which sticks to government records.</div>',
                unsafe_allow_html=True)
    with st.form("corpform", border=False):
        cq = st.text_input("Search company documents", value=ss.get("corp_q", ""), label_visibility="collapsed",
                           placeholder="Company, product or chemical, e.g. Marlboro, OxyContin, PFOA")
        if st.form_submit_button("Search company documents", type="primary", use_container_width=True):
            ss.corp_q = cq.strip()
    if ss.get("corp_q"):
        q = ss.corp_q
        with st.spinner("Searching the industry documents archive…"):
            try:
                corp_res = cached_corp(q, APP_CODE_VERSION)
            except Exception:
                corp_res = None
        if corp_res is None:
            st.caption("The industry documents archive didn't answer just now. Try again in a minute.")
        else:
            st.markdown(f'<div class="sect">INDUSTRY DOCUMENTS · “{html.escape(q)}” · {len(corp_res)}</div>',
                        unsafe_allow_html=True)
            if not corp_res:
                st.caption("Nothing came back. Try one distinctive word, or open the archive directly below.")
            for i, r in enumerate(corp_res):
                render_result(r, f"co{i}", query=q)
        st.link_button(f"More from the UCSF archive on Google: “{q}”",
                       "https://www.google.com/search?q=" + urllib.parse.quote(f"site:industrydocuments.ucsf.edu {q}"),
                       use_container_width=True)
    st.markdown('<div class="sect">THE BIG CORPORATE FILES</div>', unsafe_allow_html=True)
    for i, c in enumerate(CORPORATE):
        st.markdown(
            f'<div class="corp-card"><div class="corp-title">{html.escape(c["icon"])} {html.escape(c["title"])}</div>'
            f'<div class="corp-what">{html.escape(c["what"])}</div>'
            f'<a class="corp-src" href="{html.escape(c["url"])}" target="_blank">{html.escape(c["source"])} ↗</a></div>',
            unsafe_allow_html=True)
        if c["search"]:
            st.button(f"🔎 Search these files: “{c['search']}”", key=f"corpgo{i}", on_click=_corp_go,
                      args=(c["search"],), type="tertiary")

# ── Self-test ────────────────────────────────────────────────────────────────
with st.expander("Check which archives are working"):
    if st.button("Run check", use_container_width=True):
        from concurrent.futures import ThreadPoolExecutor
        def one(n):
            try:
                got = SOURCES[n](TEST_QUERIES[n])
                how = f" · {got[0]['kind']}" if n == "CIA" and got else ""
                return n, f"✅ {len(got)} results{how}"
            except Exception as e:
                return n, f"❌ {type(e).__name__}: {str(e)[:80]}"
        with st.spinner("Testing each archive…"), ThreadPoolExecutor(10) as ex:
            for n, msg in ex.map(one, ALL):
                st.write(f"**{n}** — {msg}")
        with st.spinner("Checking the CIA…"):
            st.caption("**CIA details:**  \n" + "  \n".join(diagnose_cia()))
        with st.spinner("Checking Corporate Secrets…"):
            try:
                direct = len(sources._ucsf_api("nicotine", 5))
                st.write(f"**Corporate Secrets (UCSF)** — direct line: ✅ {direct} results")
            except Exception as e:
                try:
                    st.write(f"**Corporate Secrets (UCSF)** — direct line ❌ {type(e).__name__}; "
                             f"web-search backup: {len(search_ucsf('nicotine', 5))} results")
                except Exception as e2:
                    st.write(f"**Corporate Secrets (UCSF)** — ❌ {type(e2).__name__}")

# ── Time Machine: the Wayback Machine as a fun link ───────────────────────────
st.divider()
st.markdown('<div class="ts-head"><b>🕰 TIME MACHINE</b><span>see government websites as they looked years ago, '
            'saved by the Wayback Machine</span></div>', unsafe_allow_html=True)
TRIPS = [
    ("CIA.gov in 1997", "https://web.archive.org/web/1997/https://www.cia.gov/"),
    ("FBI.gov in 2001", "https://web.archive.org/web/2001/https://www.fbi.gov/"),
    ("FBI Vault at launch, 2011", "https://web.archive.org/web/2011/https://vault.fbi.gov/"),
    ("NSA.gov in 2013, the Snowden year", "https://web.archive.org/web/2013/https://www.nsa.gov/"),
    ("CIA reading room, 2017", "https://web.archive.org/web/2017/https://www.cia.gov/library/readingroom/"),
    ("Open the Wayback Machine", "https://web.archive.org/"),
]
tm = st.columns(2)
for j, (label, url) in enumerate(TRIPS):
    tm[j % 2].link_button(label, url, use_container_width=True)
st.caption("Tip: every result above also has a 🕰 Saved copy link, and Find my words inside uses a saved "
           "copy automatically when a document has been taken down.")
