"""
Exhibit A — Archive Hunter (web version)
Run locally:  streamlit run app.py
"""

import html
import urllib.parse

import streamlit as st

from sources import (BROWSER_ONLY, SOURCES, TEST_QUERIES, find_passages, search_all)

st.set_page_config(page_title="Archive Hunter", page_icon="🗂️", layout="centered")

st.markdown("""
<style>
.block-container{padding-top:1.4rem;max-width:760px}
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
</style>
<div class="eyebrow">Exhibit A · Declassified</div>
<div class="brand">Archive Hunter</div>
""", unsafe_allow_html=True)

ALL = list(SOURCES)
ss = st.session_state
ss.setdefault("results", [])
ss.setdefault("status", {})
ss.setdefault("open_doc", None)
ss.setdefault("query", "")


@st.cache_data(ttl=3600, show_spinner=False)
def cached_search(q, names):
    return search_all(q, list(names))


@st.cache_data(ttl=6 * 3600, show_spinner=False, max_entries=60)
def cached_passages(url, q):
    return find_passages(url, q)


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

with st.expander("Archives to search"):
    chosen = st.pills("Archives", ALL, selection_mode="multi", default=ALL, label_visibility="collapsed")

if go and q.strip():
    ss.query = q.strip()
    ss.open_doc = None
    with st.spinner(f"Searching {len(chosen)} archives at once…"):
        ss.results, ss.status = cached_search(ss.query, tuple(chosen))

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
        key = r["url"]
        with st.container(border=True):
            st.markdown(
                f'<div class="src">{html.escape(r["source"])}</div>'
                f'<div class="res-title"><a href="{html.escape(r["url"])}" target="_blank">{html.escape(r["title"])}</a></div>'
                f'<div class="meta">{html.escape(" · ".join(x for x in (r["kind"], r["date"]) if x))}</div>'
                + (f'<div class="snip">{html.escape(r["snippet"])}</div>' if r["snippet"] else ""),
                unsafe_allow_html=True)
            cols = st.columns([1.4, 1, 1])
            if r["doc_url"]:
                if cols[0].button("🔎 Find my words inside", key=f"f{i}{key}", use_container_width=True):
                    ss.open_doc = None if ss.open_doc == key else key
            cols[1].link_button("Open", r["url"], use_container_width=True)
            if r["file_url"]:
                cols[2].link_button("Download", r["file_url"], use_container_width=True)

            if ss.open_doc == key:
                with st.spinner("Reading the document… big PDFs take up to a minute"):
                    try:
                        p = cached_passages(r["doc_url"], ss.query)
                    except Exception as e:
                        p = None
                        st.warning(f"Couldn't read this one ({type(e).__name__}). Tap Open to read it on the site.")
                if p:
                    where = f"{p['pages']} pages" if p["pages"] else "the page"
                    if p["hits"]:
                        st.success(f"{len(p['hits'])} passage(s) mention your search · read {where}")
                    elif p["note"]:
                        st.warning(p["note"])
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
                    if p["read_url"] != r["doc_url"]:
                        st.link_button("Open the PDF these came from", p["read_url"])

# ── Sites that only work in the browser ──────────────────────────────────────
st.divider()
st.markdown("**More archives** · these open in your browser with your search filled in")
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
                return n, f"✅ {len(SOURCES[n](TEST_QUERIES[n]))} results"
            except Exception as e:
                return n, f"❌ {type(e).__name__}: {str(e)[:80]}"
        with st.spinner("Testing each archive…"), ThreadPoolExecutor(10) as ex:
            for n, msg in ex.map(one, ALL):
                st.write(f"**{n}** — {msg}")
