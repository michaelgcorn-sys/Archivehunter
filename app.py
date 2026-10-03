"""
Exhibit A — Archive Hunter (web version)
Run locally:  streamlit run app.py
"""

import html
import random
import urllib.parse

import streamlit as st

import importlib

import sources

APP_CODE_VERSION = 18
if getattr(sources, "CODE_VERSION", None) != APP_CODE_VERSION:
    # Streamlit Cloud can keep an old copy of sources.py in memory after an update.
    sources = importlib.reload(sources)

from sources import (BROWSER_ONLY, SOURCES, TEST_QUERIES, diagnose_cia, find_passages, saved_copy_url,
                     search_all, top_secret_pool, vanished_pages)

st.set_page_config(page_title="Archive Hunter", page_icon="🗂️", layout="centered")

st.markdown("""
<style>
.block-container{padding-top:5rem;max-width:760px}
.eyebrow{font:700 .72rem 'Courier New',monospace;letter-spacing:.18em;color:#c4544a;text-transform:uppercase}
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
.which{font-size:.78rem;opacity:.65;margin:.3rem 0 .1rem}
</style>
<div class="eyebrow">Exhibit A · Declassified</div>
<div class="brand">Archive Hunter</div>
<div class="ver">Version 18 · updated Oct 3, 2026</div>
""", unsafe_allow_html=True)

ALL = list(SOURCES)
ss = st.session_state
ss.setdefault("results", [])
ss.setdefault("status", {})
ss.setdefault("open_doc", None)
ss.setdefault("ocr_doc", None)
ss.setdefault("query", "")


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def cached_pool():
    return top_secret_pool()


@st.fragment(run_every="30s")
def top_secret_strip():
    pool = cached_pool()
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
        f'<div class="ts-head"><b>● TOP SECRET</b><span>{len(pool)} documents marked Top Secret · '
        f'new picks every 30 seconds · swipe and tap to open</span></div>'
        f'<div class="ts-strip">{"".join(cards)}</div>', unsafe_allow_html=True)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_search(q, names):
    return search_all(q, list(names))


@st.cache_data(ttl=6 * 3600, show_spinner=False, max_entries=60)
def cached_passages(url, q, ocr=False):
    return find_passages(url, q, ocr=ocr)


with st.spinner("Pulling Top Secret documents from the archives…"):
    top_secret_strip()

# ── Search box ───────────────────────────────────────────────────────────────
QUICK = ["MKUltra", "JFK Oswald Mexico City", "Roswell", "Epstein", "Area 51", "Stargate",
         "COINTELPRO", "Bay of Pigs", "Operation Northwoods"]

with st.form("search", border=False):
    q = st.text_input("Search", value=ss.query, placeholder='Name, program or event. Use "quotes" for exact phrases',
                      label_visibility="collapsed")
    go = st.form_submit_button("Search all archives", type="primary", use_container_width=True)

pick = st.pills("Try", QUICK, label_visibility="collapsed")
if pick and pick != ss.get("last_pick"):
    ss.last_pick = pick
    q, go = pick, True

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
        ss.results, ss.status = cached_search(ss.query, tuple(chosen))

def render_result(r, uid, saved_copy=True):
    """One result card: title, source, buttons, and the "find my words" passages."""
    key = r["url"]
    with st.container(border=True):
        st.markdown(
            f'<div class="src">{html.escape(r["source"])}</div>'
            f'<div class="res-title"><a href="{html.escape(r["url"])}" target="_blank">{html.escape(r["title"])}</a></div>'
            f'<div class="meta">{html.escape(" · ".join(x for x in (r["kind"], r["date"][:4]) if x))}</div>'
            + (f'<div class="snip">{html.escape(r["snippet"])}</div>' if r["snippet"] else ""),
            unsafe_allow_html=True)
        cols = st.columns([1.5, 1, 1, 1.1])
        if r["doc_url"]:
            if cols[0].button("🔎 Find my words inside", key=f"f{uid}{key}", use_container_width=True):
                ss.open_doc = None if ss.open_doc == key else key
                ss.ocr_doc = None
        cols[1].link_button("Open", r["url"], use_container_width=True)
        if r["file_url"]:
            cols[2].link_button("Download", r["file_url"], use_container_width=True)
        if saved_copy:
            cols[3].link_button("🕰 Saved copy", saved_copy_url(r["url"]), use_container_width=True,
                                help="The Wayback Machine's most recent saved copy of this page")

        if ss.open_doc != key:
            return
        with st.spinner("Reading the document… big PDFs take up to a minute"):
            try:
                p = cached_passages(r["doc_url"], ss.query)
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
                        p = cached_passages(r["doc_url"], ss.query, True)
                    except Exception as e:
                        st.warning(f"Character recognition failed ({type(e).__name__}).")
        if p and not p.get("scanned"):
            where = f"{p['pages']} pages" if p["pages"] else "the page"
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
            if p["read_url"] not in (r["doc_url"], (p.get("wayback") or {}).get("raw")):
                st.link_button("Open the PDF these came from", p["read_url"])


@st.cache_data(ttl=6 * 3600, show_spinner=False, max_entries=40)
def cached_vanished(q):
    return vanished_pages(q)


# ── Results ──────────────────────────────────────────────────────────────────
results, status = ss.results, ss.status
if status:
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

# ── Vanished Files: deleted government pages, rescued from the Wayback Machine ──
if ss.query:
    st.divider()
    st.markdown('<div class="ts-head"><b>🕰 VANISHED FILES</b><span>government pages that have been deleted, '
                'but the Wayback Machine saved a copy</span></div>', unsafe_allow_html=True)
    st.caption("Digs through saved copies of CIA, FBI, NSA, Pentagon, State Dept, National Archives, "
               "Justice Dept and UFO-office websites for pages with your words in their web address, "
               "then keeps only the ones that no longer exist on the live site.")
    if st.button(f"Dig up deleted pages about “{ss.query}”", use_container_width=True, key="dig"):
        ss.dig_query = ss.query
    if ss.get("dig_query") == ss.query:
        with st.spinner("Digging through the Wayback Machine… this can take up to a minute"):
            try:
                gone, searched = cached_vanished(ss.query)
            except Exception as e:
                gone, searched = [], 0
                st.warning(f"The Wayback Machine didn't answer ({type(e).__name__}). Try again in a minute.")
        if gone:
            st.success(f"{len(gone)} deleted page(s) found · searched {searched} government sites")
            for i, r in enumerate(gone):
                render_result(r, f"v{i}", saved_copy=False)
        elif searched:
            st.info(f"No deleted pages found with those words in their web address "
                    f"(searched {searched} government sites). Try a shorter word, like one name or program.")

# ── Sites that only work in the browser ──────────────────────────────────────
st.divider()
st.markdown("**Not in the main search** · these archives only work on their own websites. "
            "Tap one to open it with your search filled in.")
term = urllib.parse.quote(ss.query or "")
c = st.columns(2)
for j, (name, tpl) in enumerate(BROWSER_ONLY):
    c[j % 2].link_button(name, tpl.replace("{q}", term), use_container_width=True)

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
        with st.spinner("Checking the CIA step by step…"):
            st.caption("**CIA details:**  \n" + "  \n".join(diagnose_cia()))
