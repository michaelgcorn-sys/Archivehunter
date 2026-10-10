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

APP_CODE_VERSION = 71
if getattr(sources, "CODE_VERSION", None) != APP_CODE_VERSION:
    # Streamlit Cloud can keep an old copy of sources.py in memory after an update.
    sources = importlib.reload(sources)
import catalog
if getattr(catalog, "CATALOG_VERSION", None) != APP_CODE_VERSION:
    catalog = importlib.reload(catalog)   # same stale-module problem for catalog.py
import dossier as dossier_mod
import explainers
import extras
import geo
import redactions
import newsday
import translate as tr
for _m in (dossier_mod, explainers, extras, geo, newsday, redactions, tr):
    if getattr(_m, "MODULE_VERSION", None) != APP_CODE_VERSION:
        importlib.reload(_m)

from sources import (BROWSER_ONLY, SOURCES, TEST_QUERIES, diagnose_cia, find_passages, saved_copy_url, search_gwu,
                     pdb_on_this_day, search_all, search_cia, search_pdb, search_ucsf, top_secret_pool)
from catalog import ANCIENT, CATEGORIES, CORPORATE, PICKS, TEASERS, met_gallery, met_image
from dossier import folder_files, ident_from_url, is_cia_ident, load_dossier, redaction_estimate
import streamlit.components.v1 as components

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
.st-key-popular{border:1px solid #c4544a;border-radius:8px;padding:.35rem .5rem .45rem;margin:.3rem 0 .1rem;gap:.15rem}
.st-key-popular button{min-height:0!important;padding:.05rem .55rem!important}
.st-key-popular button p,.st-key-popular button div{font-size:.82rem!important;line-height:1.5!important}
.pop-label{font-size:.8rem;font-weight:700;color:#c4544a;line-height:1.2;padding:0 0 .15rem;display:block;letter-spacing:.06em;text-transform:uppercase}
.st-key-popular [data-testid="stMarkdownContainer"]{overflow:visible;margin-bottom:0}
.st-key-popular [data-testid="stElementContainer"]{height:auto!important}
.st-key-qbox div:has(> input),.st-key-qbox [data-baseweb="input"]{border:2px solid #c8a96e!important;border-radius:10px!important;background:#1d1a14!important;box-shadow:0 0 0 3px rgba(200,169,110,.12)}
.st-key-qbox div:has(> input):focus-within,.st-key-qbox [data-baseweb="input"]:focus-within{box-shadow:0 0 0 4px rgba(200,169,110,.35)}
.st-key-qbox [data-baseweb="base-input"]{background:transparent!important}
.st-key-qbox input{font-size:1.1rem!important;height:3.2rem;padding-left:2.7rem!important;color:#f1e6cc!important;background-color:transparent!important;
 background:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='22' height='22' viewBox='0 0 24 24' fill='none' stroke='%23c8a96e' stroke-width='2.5' stroke-linecap='round'%3E%3Ccircle cx='10.5' cy='10.5' r='6.5'/%3E%3Cpath d='M15.5 15.5 21 21'/%3E%3C/svg%3E") no-repeat .8rem center!important}
.st-key-qbox input::placeholder{color:#b9ab8c!important;opacity:1}
.qtip{font-size:.82rem;color:#b9ab8c;margin:-.35rem 0 .1rem .2rem}
.st-key-dossier{border-color:#c8a96e!important;background:linear-gradient(180deg,#1d1a13,#141310)}
.dos-kicker{font:700 .72rem 'Courier New',monospace;letter-spacing:.16em;color:#c4544a}
.dos-title{font-family:Georgia,'Times New Roman',serif;font-size:1.25rem;line-height:1.3;color:#ecd9b0;margin:.1rem 0 .25rem}
.dos-img{width:100%;max-height:300px;object-fit:contain;background:#f1ece0;border-radius:4px;border:1px solid #3a3528}
.dos-ex{font-family:Georgia,serif;font-size:.86rem;line-height:1.45;opacity:.85;margin:.45rem 0}
.dos-ex span{font-family:inherit;font-style:italic;opacity:.6;font-size:.76rem}
.trail-head{font:700 .66rem 'Courier New',monospace;letter-spacing:.14em;color:#b98a4e;margin:.3rem 0 0}
[class*="-trail"] button p{font-size:.8rem;color:#c8a96e}
.st-key-dos-terms button{border-color:#6b5a38;background:#1f1b13}
.st-key-dos-terms button p{font-weight:600;color:#ecd9b0}
.st-key-scroller{height:0;overflow:hidden;margin:0!important}
[class*="st-key-dos-near"] button,[class*="st-key-dos-near"] button *{justify-content:flex-start!important;text-align:left!important}
[class*="st-key-dos-near"] button p{font-size:.88rem}
.st-key-dos-top{justify-content:space-between}
.st-key-favstore{display:none}
.st-key-favbox{border-color:#c8a96e!important;background:#15130f}
.fav-head{font-family:'Courier New',monospace;font-size:.8rem;letter-spacing:.14em;color:#c8a96e;font-weight:700}
.fav-t{font-size:.92rem;line-height:1.3}.fav-t a{color:#ecd9b0;text-decoration:none}
.fav-t span{display:block;font-size:.72rem;opacity:.6}
[class*="st-key-fav-row-"]{flex-wrap:nowrap!important;border-top:1px solid #2a251c;padding-top:.3rem}
[class*="st-key-fav-row-"] > div:first-child{flex:1 1 auto;min-width:0}
.st-key-dos-top button p{color:#c8a96e}
[class*="-explainer"]{border-color:#5a6b7d!important;background:#15191e}
.exp-head{font:700 .74rem 'Courier New',monospace;letter-spacing:.14em;color:#9fb3c8;margin-bottom:.35rem}
.exp-text{font-family:Georgia,'Times New Roman',serif;font-size:.95rem;line-height:1.55;color:#e3e8ee}
.exp-src{font-size:.76rem;opacity:.7;margin:.35rem 0 .2rem}
.exp-src a{color:#9fb3c8!important}
.exp-sub{font:700 .64rem 'Courier New',monospace;letter-spacing:.12em;color:#9fb3c8;margin:.6rem 0 .2rem}
.exp-links{display:flex;flex-direction:column;gap:.3rem}
.exp-link{font-size:.86rem;color:#dfe6ee!important;text-decoration:none;border-left:2px solid #5a6b7d;padding-left:.5rem}
/* ── "Thinking" signals: spy-style instead of Streamlit's runner and gray circle ── */
/* ── Always-on status light, top-left: STANDING BY when idle, DECRYPTING + sweeping radar while loading ── */
[data-testid="stStatusWidgetRunningIcon"]{display:none!important}
.stApp::before{content:"STANDING BY";position:fixed;top:16px;left:16px;z-index:1000001;pointer-events:none;
 font:700 .66rem 'Courier New',monospace;letter-spacing:.16em;color:rgba(200,169,110,.45);padding-left:24px;line-height:16px}
.stApp::after{content:"";position:fixed;top:16px;left:16px;width:16px;height:16px;border-radius:50%;z-index:1000002;
 pointer-events:none;box-sizing:border-box;border:1px solid rgba(90,220,130,.3);
 background:radial-gradient(circle,rgba(90,220,130,.45) 0 1.5px,transparent 2px)}
.stApp[data-test-script-state="running"]::before,.stApp:has([data-testid="stStatusWidget"])::before{
 content:"DECRYPTING";color:#e0574c;animation:ah-blink 1.1s steps(2,start) infinite}
.stApp[data-test-script-state="running"]::after,.stApp:has([data-testid="stStatusWidget"])::after{
 border-color:rgba(90,220,130,.65);
 background:conic-gradient(from 0deg,rgba(90,220,130,0) 0deg,rgba(90,220,130,.8) 70deg,rgba(90,220,130,0) 71deg),
            radial-gradient(circle,rgba(90,220,130,.95) 0 1.5px,transparent 2px);
 animation:ah-sweep 1.4s linear infinite}
[data-testid="stSpinnerIcon"]{border:1px solid rgba(90,220,130,.55)!important;border-radius:50%!important;
 width:1.35rem!important;height:1.35rem!important;
 background:conic-gradient(from 0deg,rgba(90,220,130,0) 0deg,rgba(90,220,130,.7) 70deg,rgba(90,220,130,0) 71deg),
            linear-gradient(rgba(90,220,130,.25),rgba(90,220,130,.25)) center/100% 1px no-repeat,
            linear-gradient(rgba(90,220,130,.25),rgba(90,220,130,.25)) center/1px 100% no-repeat,
            radial-gradient(circle,rgba(90,220,130,.08) 0 60%,transparent 61%)!important;
 animation:ah-sweep 1.4s linear infinite!important}
@keyframes ah-sweep{to{transform:rotate(360deg)}}
@keyframes ah-blink{0%{opacity:1}50%{opacity:.25}100%{opacity:1}}

.dos-part{font-size:.82rem;color:#c8a96e;margin:.5rem 0 .3rem}
.st-key-dos-pn button{min-width:9rem}
.ww-head{font:700 .66rem 'Courier New',monospace;letter-spacing:.14em;color:#b98a4e;margin:.6rem 0 .1rem}
.redact{margin:.5rem 0}
.redact-label{font:700 .7rem 'Courier New',monospace;letter-spacing:.12em;color:#e6dccb}
.redact-bar{height:10px;background:#2a2620;border:1px solid #4a4030;border-radius:2px;margin:.3rem 0;overflow:hidden}
.redact-bar span{display:block;height:100%;background:repeating-linear-gradient(90deg,#000 0 14px,#111 14px 16px)}
.redact-note{font-size:.72rem;opacity:.6}
.st-key-otd-box{border-color:#5a4a2e!important;background:#15130f}
.otd-h{font:700 .66rem 'Courier New',monospace;letter-spacing:.13em;color:#c4544a;margin-bottom:.35rem}
.otd-t{font-family:Georgia,serif;font-size:1.02rem;color:#ecd9b0;line-height:1.3}
.otd-x{font-size:.86rem;margin:.3rem 0;color:#e6dccb}
.otd-src{font-size:.72rem;opacity:.6;margin:.3rem 0 .4rem}
.otd-src a{color:inherit!important}
.otd-list{display:flex;flex-direction:column;gap:.35rem}
.otd-n{font-family:Georgia,serif;font-size:.88rem;line-height:1.4;color:#e3e3e3!important;text-decoration:none}
.st-key-mystery{border-color:#7a3a33!important;background:#191210}
[class*="-tile-mys"] button{background:linear-gradient(160deg,#25140f,#140c0a);border-color:#6b3a30}
.redbar{background:#000;border-radius:2px;padding:0 .2rem;box-shadow:0 0 0 1px #333}
.myst-jargon{font-size:.8rem;color:#b9ab8c;margin:.25rem 0}
.st-key-mystery [data-testid="stRadio"] label p{font-size:.92rem}
.exp-link-line{font-size:.92rem;color:#e3e8ee;margin:.1rem 0 .45rem}
.otd-row{border-top:1px solid #3a3226;padding:.55rem 0 .4rem}
.otd-topic{font:700 .78rem 'Courier New',monospace;letter-spacing:.12em;color:#e8d3a0;text-transform:uppercase;margin-bottom:.3rem}
.otd-pair{display:grid;grid-template-columns:1fr 1fr;gap:.8rem;font-family:Georgia,serif;font-size:.88rem;line-height:1.4;color:#e6dccb}
.otd-pair .otd-h{display:block;font:700 .62rem 'Courier New',monospace;letter-spacing:.12em;color:#c4544a;margin-bottom:.15rem}
.otd-pair a{color:#e6dccb!important}
.otd-dim{opacity:.6;font-size:.78rem}
.otd-quiet{opacity:.75;font-style:italic}
@media (max-width:640px){.otd-pair{grid-template-columns:1fr;gap:.45rem}}

.st-key-otd-places button{border-color:#5a4a2e;background:#1c1810}
.st-key-otd-places button p{font-weight:600;color:#ecd9b0}
.ba-head{font:700 .9rem 'Courier New',monospace;letter-spacing:.18em;color:#e8e2d4;margin-top:.4rem}
.ba-tag{font:700 .68rem 'Courier New',monospace;letter-spacing:.14em;padding:.3rem .55rem;border-radius:3px;display:inline-block;margin:.4rem 0}
.ba-tag.shut{background:#000;color:#c4544a;border:1px solid #4a1f1b}
.ba-tag.open{background:#13261a;color:#7fd99a;border:1px solid #2c5a3a}
.ba-sub{font:700 .64rem 'Courier New',monospace;letter-spacing:.14em;color:#b98a4e;margin:.7rem 0 .15rem}
.ba-text{font-size:.9rem;line-height:1.45;opacity:.9}
.nara-photo{display:block;text-decoration:none!important;border:1px solid #3d5a80;border-bottom:none;border-radius:8px 8px 0 0;overflow:hidden;background:#0b0f15}
.nara-photo img{display:block;width:100%;height:104px;object-fit:cover;filter:sepia(.25) contrast(1.05)}
.nara-photo span{display:block;font-size:.68rem;line-height:1.25;color:#9fb3cc;padding:.25rem .4rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
[class*="st-key-nara-cell-"]{gap:0!important}
[class*="st-key-nara-cell-"] [data-testid="stMarkdownContainer"]{margin-bottom:0!important}
[class*="st-key-nara-cell-"] [data-testid="stElementContainer"]{margin:0!important}
[class*="st-key-nara-cell-"] .stMarkdown{margin-bottom:-1rem}
[class*="st-key-nara-cell-"]:has(.nara-photo) button{border-top-left-radius:0!important;border-top-right-radius:0!important}
.st-key-nara-box{border-color:#3d5a80!important;background:linear-gradient(180deg,#121a26,#0f1218)}
.nara-kicker{font:700 .72rem 'Courier New',monospace;letter-spacing:.18em;color:#8fb3de}
.nara-title{font-family:Georgia,serif;font-size:1.25rem;color:#e6eef8;margin:.15rem 0 .2rem}
[class*="nara-tile-"] button{height:auto!important;min-height:132px;align-items:flex-start;justify-content:flex-start;text-align:left;padding:.7rem .75rem;
 background:linear-gradient(160deg,#17202d,#10151d);border:1px solid #2e4260;border-radius:8px}
[class*="nara-tile-"] button *{white-space:normal!important;overflow:visible!important;text-overflow:clip!important}
[class*="nara-tile-"] button p{font-size:.74rem;line-height:1.3;opacity:.85;margin:0;text-align:left}
[class*="nara-tile-"] button p strong{display:block;font-size:.9rem;color:#cfe0f5;opacity:1;margin:.3rem 0 .25rem}
.which{font-size:.82rem;line-height:1.35;opacity:.7;margin:.4rem 0 .2rem}
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
.anc-lang{font-size:.76rem;opacity:.65;font-style:italic;margin:.1rem 0 .45rem}
.anc-src{font-size:.8rem;font-weight:600;color:#b98a4e!important;text-decoration:none}
.met-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;margin-top:.6rem}
.met-tile{display:flex;flex-direction:column;background:#1c1710;border:1px solid #4a3a22;border-radius:6px;
          overflow:hidden;text-decoration:none!important;color:#e6d6b8!important}
.met-tile img{width:100%;height:140px;object-fit:cover;background:#120f0a}
.met-tile span{font-size:.72rem;padding:.4rem .5rem;line-height:1.3}
</style>
<div class="eyebrow">Exhibit A · Declassified</div>
<a class="brand-link" href="./" target="_self"><div class="brand">Archive Hunter</div></a>
<div class="ver">Version 71 · Archive Hunter 2.0 · updated Oct 5, 2026</div>
""", unsafe_allow_html=True)

ALL = list(SOURCES)
ss = st.session_state
ss.setdefault("results", [])
ss.setdefault("status", {})
ss.setdefault("open_doc", None)
ss.setdefault("ocr_doc", None)
ss.setdefault("query", "")


@st.cache_data(ttl=1800, show_spinner=False)    # new random batch every 30 minutes
def cached_pool(v=APP_CODE_VERSION):    # version in the key: an update throws out old answers
    return top_secret_pool()


def _tile_href(r):
    ident = ident_from_url(r["url"])
    return f"?doc={ident}" if ident else r["url"]      # CIA files open as a dossier inside the app


def _tile_target(r):
    return "_self" if ident_from_url(r["url"]) else "_blank"


@st.fragment(run_every="30s")
def top_secret_strip():
    pool = cached_pool(APP_CODE_VERSION)
    if not pool:
        return
    hot = [r for r in pool if r.get("interest", 0) > 0]
    rest = [r for r in pool if r.get("interest", 0) <= 0]
    picks = random.sample(hot, min(8, len(hot)))                    # mostly exciting ones
    picks += random.sample(rest, min(10 - len(picks), len(rest)))
    random.shuffle(picks)
    cards = []
    for r in picks:
        if r.get("thumb"):
            img = f'<div class="ts-img" style="background-image:url(\'{html.escape(r["thumb"])}\')">'
        else:
            img = f'<div class="ts-img folder">{html.escape(r["source"].upper())}'
        year = f" · {r['date']}" if r["date"] else ""
        cards.append(
            f'<a class="ts-card" href="{html.escape(_tile_href(r))}" target="{_tile_target(r)}">{img}'
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



# ════════════════════════════════════════════════════════════════════════════
# Dossier: one CIA document opened inside the app, with a trail to follow
# ════════════════════════════════════════════════════════════════════════════
ss.setdefault("trail", [])

# ── Saved files (⭐): kept in this browser's own storage, so they survive refreshes and app updates ──
FAV_KEY = "archivehunter_saved_v1"
FAV_JS = """
export default function(component) {
  const { data, setStateValue } = component;
  const K = "%s";
  let v;
  try {
    if (data && typeof data.save === "string") { localStorage.setItem(K, data.save); }
    v = localStorage.getItem(K) || "[]";
  } catch (e) { v = "__nostorage__"; }
  if (window.__ahFavSent !== v) { window.__ahFavSent = v; setStateValue("favs", v); }
}
""" % FAV_KEY


@st.cache_resource
def _fav_component():
    return st.components.v2.component("ah_favstore", js=FAV_JS)


ss.setdefault("favs", [])


def fav_sync():
    """Load the saved list from this browser once, and write it back whenever it changes."""
    import json
    save = json.dumps(ss.favs) if ss.pop("fav_dirty", False) else None
    try:
        res = _fav_component()(key="favstore", data={"save": save}, default={"favs": None},
                               on_favs_change=lambda: None)
        raw = res.get("favs") if isinstance(res, dict) else getattr(res, "favs", None)
    except Exception:
        ss.fav_storage = False
        return
    if raw == "__nostorage__":
        ss.fav_storage = False
    elif raw is not None:
        ss.fav_storage = True
        if not ss.get("favs_loaded"):
            try:
                got = json.loads(raw)
                ss.favs = [f for f in got if isinstance(f, dict) and f.get("url")] if isinstance(got, list) else []
            except ValueError:
                ss.favs = []
            ss.favs_loaded = True


def is_fav(url):
    return any(f["url"] == url for f in ss.favs)


def toggle_fav(item):
    """item: dict with url, title, source, date (and ident for CIA files)."""
    if is_fav(item["url"]):
        ss.favs = [f for f in ss.favs if f["url"] != item["url"]]
    else:
        keep = {k: str(item.get(k) or "")[:300] for k in ("url", "title", "source", "date", "ident")}
        ss.favs = [keep] + ss.favs[:199]
    ss.fav_dirty = True


def fav_button(item, key, **kw):
    on = is_fav(item["url"])
    st.button("★ Saved" if on else "☆ Save", key=key, on_click=toggle_fav, args=(item,), type="tertiary",
              help="Remove from your saved files" if on else "Keep this in your saved files on this device", **kw)


fav_sync()
KIND_ICON = {"codeword": "🔐", "person": "👤", "place": "🌍", "name": "🏷"}


@st.cache_data(ttl=24 * 3600, show_spinner=False, max_entries=200)
def cached_dossier(ident, v=APP_CODE_VERSION):
    return load_dossier(ident)


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False, max_entries=300)
def cached_redaction(pdf_url, v=APP_CODE_VERSION):
    return redaction_estimate(pdf_url)


def redaction_meter(d):
    if ss.get("measure") != d["ident"]:
        st.button("⬛ How much was blacked out?", key="dos-redact", on_click=lambda: ss.update(measure=d["ident"]))
        return
    with st.spinner("Measuring the black boxes on each page…"):
        try:
            m = cached_redaction(d["pdf"], APP_CODE_VERSION)
        except Exception:
            st.caption("Couldn't measure this one (the PDF didn't load).")
            return
    pct, pages = m["pct"], m["pages"]
    of = f"first {pages} of {m['total_pages']} pages" if m["total_pages"] > pages else f"all {pages} page{'s' if pages != 1 else ''}"
    if pct == 0:
        msg, fill = "No blacked-out passages found", 0
    elif pct < 1:
        msg, fill = "Under 1% blacked out: a few names or words", 2
    else:
        msg, fill = f"About {pct:.0f}% blacked out", min(100, pct)
    st.markdown(f'<div class="redact"><div class="redact-label">⬛ CENSOR METER · {html.escape(msg)}</div>'
                f'<div class="redact-bar"><span style="width:{fill}%"></span></div>'
                f'<div class="redact-note">Approximate: measured from the scans ({of}). Dark photos or stamps can '
                f'throw it off.</div></div>', unsafe_allow_html=True)


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False, max_entries=100)
def cached_card(ident, title, year, v=APP_CODE_VERSION):
    return extras.share_card(title, year, "CIA", extras.first_page_image(ident))


@st.cache_data(ttl=24 * 3600, show_spinner=False, max_entries=200)
def cached_folder(ident, v=APP_CODE_VERSION):
    return folder_files(ident)


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False, max_entries=500)
def cached_translation(text, provider, v=APP_CODE_VERSION):
    return tr.translate(text)


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False, max_entries=200)
def cached_wiki(article, v=APP_CODE_VERSION):
    return explainers.wiki_summary(article)


@st.cache_data(ttl=24 * 3600, show_spinner=False, max_entries=200)
def cached_briefings(term, v=APP_CODE_VERSION):
    return search_gwu(term, limit=3)


def explainer_card(prog, prefix):
    """Plain-English background on a program, before the raw documents."""
    if not prog:
        return
    try:
        w = cached_wiki(prog["article"], APP_CODE_VERSION)
    except Exception:
        w = None
    try:
        briefs = cached_briefings(prog["term"].title() if len(prog["term"]) > 4 else prog["term"], APP_CODE_VERSION)
    except Exception:
        briefs = []
    if not w and not briefs:
        return
    with st.container(border=True, key=f"{prefix}-explainer"):
        term, name = prog["term"], prog["name"]
        codename = term.replace("-", "").replace(" ", "").upper() not in name.replace("-", "").replace(" ", "").upper()
        if re.search(r"\b19\d\d$", term):      # a place + year deep dive
            st.markdown(f'<div class="exp-head">📖 WHAT WAS HAPPENING · {html.escape(term.upper())}</div>'
                        f'<div class="exp-link-line">In {html.escape(term.rsplit(" ", 1)[1])}, '
                        f'{html.escape(term.rsplit(" ", 1)[0])} meant {html.escape(name)}. Here’s the background:</div>',
                        unsafe_allow_html=True)
        elif codename:      # e.g. AQUATONE -> "the U-2 spy plane program": say how they're connected
            st.markdown(f'<div class="exp-head">📖 WHAT WAS {html.escape(term)}?</div>'
                        f'<div class="exp-link-line"><b>{html.escape(term)}</b> was the code name for '
                        f'{html.escape(name)}. Here’s the background:</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="exp-head">📖 WHAT WAS {html.escape(name.upper())}?</div>', unsafe_allow_html=True)
        if w:
            text = w["extract"]
            if len(text) > 700:
                text = text[:700].rsplit(". ", 1)[0] + "."
            st.markdown(f'<div class="exp-text">{html.escape(text)}</div>'
                        f'<div class="exp-src">Background from Wikipedia · <a href="{html.escape(w["url"])}" '
                        f'target="_blank">Read the full article ↗</a></div>', unsafe_allow_html=True)
        if briefs:
            st.markdown('<div class="exp-sub">EXPERT BRIEFINGS · National Security Archive (historians at GWU)</div>',
                        unsafe_allow_html=True)
            rows = "".join(f'<a class="exp-link" href="{html.escape(b["url"])}" target="_blank">'
                           f'{html.escape(b["title"][:110])} ↗</a>' for b in briefs[:3])
            st.markdown(f'<div class="exp-links">{rows}</div>', unsafe_allow_html=True)


def _scroll(selector=None):
    """Bring the top of the page (or an element) into view after a tap lower down."""
    target = (f"var el=d.querySelector('{selector}'); if(el) el.scrollIntoView({{behavior:'smooth'}});"
              if selector else "var m=d.querySelector('[data-testid=\"stMain\"]'); if(m) m.scrollTo(0,0); window.parent.scrollTo(0,0);")
    code = f"<script>var d=window.parent.document; setTimeout(function(){{{target}}}, 120);/*{random.random()}*/</script>"
    with st.container(key="scroller"):           # our own fixed script, never user input
        if hasattr(st, "iframe"):
            st.iframe(code, height=1)
        else:
            components.html(code, height=0)


def open_dossier(ident):
    st.query_params["doc"] = ident
    ss.scroll_top = True


def close_dossier():
    st.query_params.pop("doc", None)


def follow_term(term):
    """Run a main search for a term from the dossier, and record it on the trail."""
    ss.trail.append({"kind": "search", "q": term, "label": term})
    ss.qbox = term
    ss.run_quick = True
    ss.main_tabs = TAB_SEARCH
    st.query_params.pop("doc", None)
    ss.scroll_results = True


def goto_trail(i):
    step = ss.trail[i]
    ss.trail = ss.trail[:i]          # the step re-adds itself when opened
    if step["kind"] == "doc":
        open_dossier(step["ident"])
    else:
        follow_term(step["q"])


def show_trail(prefix):
    if len(ss.trail) < 2:
        return
    st.markdown('<div class="trail-head">🧵 YOUR TRAIL · tap a step to go back</div>', unsafe_allow_html=True)
    with st.container(horizontal=True, wrap=True, gap="small", key=f"{prefix}-trail"):
        steps = ss.trail[-8:]
        offset = len(ss.trail) - len(steps)
        for j, step in enumerate(steps):
            icon = "📄" if step["kind"] == "doc" else "🔎"
            last = j == len(steps) - 1
            st.button(f"{icon} {step['label'][:32]}{' ←' if last else ''}", key=f"{prefix}-step-{offset + j}",
                      on_click=goto_trail, args=(offset + j,), disabled=last, type="tertiary")


def share_url(ident):
    try:
        base = str(st.context.url or "").split("?")[0].replace("/~/+", "").rstrip("/") + "/"
    except Exception:
        base = ""
    if not base.startswith("http"):
        base = ""
    return f"{base}?doc={ident}"


def render_dossier(ident):
    with st.container(border=True, key="dossier"):
        try:
            with st.spinner("Opening the file…"):
                d = cached_dossier(ident, APP_CODE_VERSION)
        except Exception:
            st.warning("Couldn't open this file just now. Try again in a minute.")
            st.button("✕ Close", key="dos-close-err", on_click=close_dossier)
            return
        if not ss.trail or ss.trail[-1].get("ident") != ident:
            ss.trail.append({"kind": "doc", "ident": ident, "label": d["title"]})
        with st.container(horizontal=True, vertical_alignment="center", key="dos-top"):
            st.markdown(f'<div class="dos-kicker">🕵 DOSSIER · {html.escape(d["doc_id"])}</div>', unsafe_allow_html=True)
            fav_button({"url": d["view"], "title": d["title"], "source": "CIA", "date": (d["date"] or "")[:4],
                        "ident": ident}, key="dos-fav")
            st.button("✕ Close", key="dos-close", on_click=close_dossier, type="tertiary")
        show_trail("dos")
        c1, c2 = st.columns([2, 3])
        c1.markdown(f'<a href="{html.escape(d["view"])}" target="_blank"><img class="dos-img" '
                    f'src="{html.escape(d["thumb"])}" alt="First page"></a>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="dos-title">{html.escape(d["title"])}</div>'
                        f'<div class="meta">CIA · {html.escape(d["date"] or "date unknown")}</div>'
                        + (f'<div class="dos-ex"><b>In this brief:</b> {html.escape(" · ".join(d["brief_topics"]))}</div>'
                           if d.get("brief_topics") else
                           f'<div class="dos-ex">“{html.escape(d["excerpt"][:320])}…”'
                           f'<span> · from the first page</span></div>' if d["excerpt"] else
                           '<div class="dos-ex"><span>This is an old scan and its text is too faded for the computer '
                           'to read cleanly, so there\'s no quote here. Tap the page picture to read the original.</span></div>'),
                        unsafe_allow_html=True)
            st.markdown(f'<div class="links"><a href="{html.escape(d["view"])}" target="_blank">📄 Read this document ↗</a> '
                        f'<a href="{html.escape(d["pdf"])}" target="_blank">⬇ PDF</a></div>', unsafe_allow_html=True)

        try:
            folder = cached_folder(ident, APP_CODE_VERSION)
        except Exception:
            folder = []
        ids = [ident_from_url(r["url"]) for r in folder]
        pos = ids.index(ident) if ident in ids else -1
        if pos >= 0 and len(folder) > 1:
            st.markdown(f'<div class="dos-part">📑 Part {pos + 1} of {len(folder)} in this CIA file. Long reports were often '
                        f'scanned as separate documents; page through the rest here.</div>', unsafe_allow_html=True)
            with st.container(horizontal=True, gap="small", key="dos-pn"):
                st.button("◀ Previous part", key="dos-prev", disabled=pos == 0,
                          on_click=open_dossier, args=(ids[pos - 1] if pos > 0 else ident,))
                st.button("Next part ▶", key="dos-next", type="primary", disabled=pos >= len(folder) - 1,
                          on_click=open_dossier, args=(ids[pos + 1] if pos < len(folder) - 1 else ident,))

        redaction_meter(d)
        codewords = " ".join(t for t, k in d["terms"] if k == "codeword")
        explainer_card(explainers.find_program(d["title"]) or explainers.find_program(codewords), "dos")

        sample = (d["text"] or "")[:3000]
        if d.get("readable", True) and tr.looks_foreign(sample):
            label = tr.provider_label()
            if label:
                if st.button(f"🌐 Translate the first page to English ({label})", key="dos-tr", width="stretch"):
                    ss.dos_tr = ident
                if ss.get("dos_tr") == ident:
                    try:
                        text, lang = cached_translation(sample, tr.active_provider(), APP_CODE_VERSION)
                        st.markdown(f'<div class="passage"><div class="pg">MACHINE TRANSLATION'
                                    f'{" FROM " + html.escape(lang.upper()) if lang else ""}</div>{html.escape(text)}</div>',
                                    unsafe_allow_html=True)
                    except Exception as e:
                        st.caption(f"Translation didn't work just now ({type(e).__name__}).")
            else:
                st.caption("🌐 This document isn't in English. In-app translation isn't switched on yet.")

        if d["terms"]:
            st.markdown('<div class="sect">🧵 FOLLOW THE TRAIL</div>'
                        '<div class="intro">Names and codewords from this document. Tap one to search every archive.</div>',
                        unsafe_allow_html=True)
            with st.container(horizontal=True, wrap=True, gap="small", key="dos-terms"):
                for i, (term, kind) in enumerate(d["terms"]):
                    st.button(f"{KIND_ICON[kind]} {term}", key=f"dos-term-{i}", on_click=follow_term, args=(term,))
        else:
            st.caption("No clear names or codewords could be read from this scan. Try the documents filed nearby.")

        others = [(i, r) for i, r in enumerate(folder) if ids[i] != ident]
        if others:
            st.markdown(f'<div class="sect">📑 THE REST OF THIS FILE · {len(folder)} documents</div>', unsafe_allow_html=True)
            for i, r in others[:12]:
                st.button(f"Part {i + 1} · {r['title'][:85]}" + (f"  ·  {r['date'][:4]}" if r["date"] else ""),
                          key=f"dos-near-{i}", on_click=open_dossier, args=(ids[i],), width="stretch",
                          type="tertiary")

        with st.expander("🔗 Share this find"):
            st.code(share_url(ident), language=None, wrap_lines=True)
            st.caption("Copy this link and text or email it. It opens straight to this document in Archive Hunter "
                       "(they need to be invited to the app).")
            if st.button("🖼 Make a DECLASSIFIED image to post", key="dos-card"):
                ss.card_for = ident
            if ss.get("card_for") == ident:
                with st.spinner("Making the image…"):
                    try:
                        png = cached_card(ident, d["title"], (d["date"] or "")[:4], APP_CODE_VERSION)
                        st.image(png, width="stretch")
                        st.download_button("⬇ Save the image", png, file_name=f"declassified-{d['doc_id']}.png",
                                           mime="image/png", key="dos-card-dl", width="stretch")
                    except Exception as e:
                        st.caption(f"Couldn't make the image just now ({type(e).__name__}).")
    if ss.pop("scroll_top", False):
        _scroll()


_doc = st.query_params.get("doc")
if is_cia_ident(_doc):
    render_dossier(_doc)

@st.cache_data(ttl=24 * 3600, show_spinner=False, max_entries=10)
def cached_mystery(day, v=APP_CODE_VERSION):
    return extras.daily_mystery(day)


def daily_mystery_card():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    today = datetime.now(ZoneInfo("America/New_York")).date()
    week = today.isoformat()            # key for today's guess
    try:
        m = cached_mystery(today, APP_CODE_VERSION)
    except Exception:
        m = None
    if not m:
        return
    with st.container(border=True, key="mystery"):
        bar = '<span class="redbar">' + "&nbsp;" * 14 + "</span>"
        title_html = bar.join(html.escape(p) for p in m["title_parts"])
        st.markdown(f'<div class="exp-head" style="color:#c4544a">🕵 DAILY MYSTERY · {today.strftime("%b %-d").upper()}</div>'
                    f'<div class="intro">A real CIA document from <b>{html.escape(m["year"])}</b>. A program codeword '
                    f'has been blacked out of its title. Use the year and the clues to work out which one.</div>'
                    f'<div class="dos-title">{title_html}</div>'
                    + "".join(f'<div class="myst-jargon"><b>{html.escape(k)}</b> = {html.escape(v)}</div>'
                              for k, v in m.get("jargon", [])),
                    unsafe_allow_html=True)
        labels = {f"{o} · {desc}": o for o, desc in m["options"]}
        guess = st.radio("Which codeword?", list(labels), index=None, key=f"guess2-{week}")
        if guess:
            g = labels[guess]
            what = dict(m["options"])[m["answer"]]
            if g == m["answer"]:
                st.success(f"✅ Correct: {m['answer']}, the CIA's code name for {what}.")
            else:
                st.error(f"❌ Not quite. It was {m['answer']}, the CIA's code name for {what}.")
            ident = ident_from_url(m["url"])
            if ident:
                st.button("🕵 Open the file", key="mystery-open", on_click=open_dossier, args=(ident,))
            explainer_card(explainers.find_program(m["answer"]), "mys")
        st.caption("A new mystery every day.")


with st.spinner("Pulling Top Secret documents from the archives…"):
    top_secret_strip()
daily_mystery_card()


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
        ident = ident_from_url(r["url"])
        fav_button({"url": r["url"], "title": r["title"], "source": r["source"], "date": (r.get("date") or "")[:4],
                    "ident": ident or ""}, key=f"s{uid}{key}")
        if ident:
            st.button("🕵 Open the dossier · follow the trail", key=f"d{uid}{key}", on_click=open_dossier,
                      args=(ident,), width="stretch")
        if r["doc_url"]:
            if st.button("🔎 Find my words inside", key=f"f{uid}{key}", width="stretch"):
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
                         width="stretch"):
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
            if p["hits"] and tr.looks_foreign(" ".join(t for _pg, t, _m in p["hits"][:6])) and tr.provider_label():
                if st.button(f"🌐 Translate these passages to English ({tr.provider_label()})", key=f"t{uid}{key}",
                             width="stretch"):
                    ss.tr_doc = key
                if ss.get("tr_doc") == key:
                    joined = "\n\n".join(t for _pg, t, _m in p["hits"][:12])
                    try:
                        text, lang = cached_translation(joined, tr.active_provider(), APP_CODE_VERSION)
                        st.markdown(f'<div class="passage"><div class="pg">MACHINE TRANSLATION'
                                    f'{" FROM " + html.escape(lang.upper()) if lang else ""}</div>'
                                    f'{html.escape(text).replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
                    except Exception as e:
                        st.caption(f"Translation didn't work just now ({type(e).__name__}).")
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


def _open_mystery():
    ss.main_tabs = TAB_EXPLORE


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
    c2.button("🎲 Random day", on_click=_pdb_random, width="stretch")
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
    rolled = ss.get("otd_roll")
    if rolled:                                               # 🎲 a brief from a random day instead
        r = rolled
    d = _brief_date(r)
    yr = d.year if d else (r["date"] or "")
    if rolled:
        head = f"🎲 A RANDOM DAY · {d.strftime('%B %-d, %Y').upper() if d else yr}"
    else:
        head = f"📜 ON THIS DAY · {today.strftime('%B %-d').upper()}, {yr}"
    st.markdown(f'<div class="sect">{head}</div>', unsafe_allow_html=True)
    ident = ident_from_url(r["url"])
    topics = (r["snippet"].replace("In this brief: ", "").split(" · ") if r["snippet"].startswith("In this brief") else [])
    if ident and len(topics) < 2:
        try:
            topics = cached_dossier(ident, APP_CODE_VERSION).get("brief_topics") or topics
        except Exception:
            pass
    topics = [t for t in topics if t][:6]
    with st.container(border=True, key="otd-box"):
        nice_title = re.sub(r"'S\b", "’s", r["title"].title())
        st.markdown(f'<div class="otd-h">🔒 WHAT THE CIA TOLD THE PRESIDENT THAT MORNING</div>'
                    f'<div class="otd-t">{html.escape(nice_title)}</div>', unsafe_allow_html=True)
        if ident:
            st.button("🕵 Open the brief", key="otd-open", on_click=open_dossier, args=(ident,),
                      type="primary", width="stretch")
        if topics:
            st.markdown('<div class="otd-x">In this brief · tap a place to dig into what was happening there</div>',
                        unsafe_allow_html=True)
            with st.container(horizontal=True, wrap=True, gap="small", key="otd-places"):
                for i, t in enumerate(topics):
                    q = f"{t} {yr}" if yr else t
                    st.button(f"🌍 {t}", key=f"otd-place-{i}", on_click=follow_term, args=(q,))
        with st.container(horizontal=True, gap="small", key="otd-actions"):
            st.button("🎲 Roll another date", key="otd-roll", on_click=_roll_brief, type="tertiary")
            if rolled:
                st.button("↩ Back to today", key="otd-today", on_click=lambda: ss.pop("otd_roll", None), type="tertiary")
    st.button("📜 Pick any date", key="otd-more", on_click=_open_pdb_at, args=(d,), width="stretch")


def _roll_brief():
    """Swap in the brief from a random day of the released run."""
    from datetime import date, timedelta
    a, b = date.fromisoformat(sources.PDB_FIRST), date.fromisoformat(sources.PDB_LAST)
    for _ in range(4):                       # a few tries in case a date has no brief nearby
        day = a + timedelta(days=random.randint(0, (b - a).days))
        try:
            got = cached_pdb(day.isoformat(), APP_CODE_VERSION)
        except Exception:
            got = []
        if got:
            ss.otd_roll = got[0]
            return


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False, max_entries=60)
def cached_wiki_day(d, v=APP_CODE_VERSION):
    return newsday.wiki_day(d)


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False, max_entries=60)
def cached_nyt(d, v=APP_CODE_VERSION):
    return newsday.nyt_front(d)


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False, max_entries=60)
def cached_public(d, topics, v=APP_CODE_VERSION):
    return newsday.public_on_topics(d, list(topics))


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False, max_entries=200)
def cached_nyt_topic(d, topic, v=APP_CODE_VERSION):
    return newsday.nyt_on_topic(d, topic)


def news_day(d):
    """Front-page headlines (New York Times, when a key is set) or Wikipedia's record of the day."""
    if not d:
        st.caption("No date to match.")
        return
    heads = []
    if newsday.nyt_available():
        try:
            heads = cached_nyt(d, APP_CODE_VERSION)
        except Exception:
            heads = []
    if heads:
        rows = "".join(f'<a class="otd-n" href="{html.escape(u)}" target="_blank">“{html.escape(h)}”</a>' for h, u in heads)
        st.markdown(f'<div class="otd-list">{rows}</div><div class="otd-src">Front page, The New York Times, '
                    f'{d.strftime("%B %-d, %Y")}</div>', unsafe_allow_html=True)
        return
    try:
        events = cached_wiki_day(d, APP_CODE_VERSION)
    except Exception:
        events = []
    if events:
        rows = "".join(f'<div class="otd-n">• {html.escape(e)}</div>' for e in events)
        url = "https://en.wikipedia.org/wiki/" + d.strftime("%B_%Y") + "#" + d.strftime("%B_") + str(d.day) + "," + d.strftime("_%Y")
        st.markdown(f'<div class="otd-list">{rows}</div><div class="otd-src">The day’s news, from '
                    f'<a href="{html.escape(url)}" target="_blank">Wikipedia’s day-by-day record</a></div>',
                    unsafe_allow_html=True)
    else:
        st.caption("No news record found for that day.")


def when_where(rows, query):
    """Timeline (decades) and map (countries named) for a set of results; both filter the list."""
    fkey = str(__import__("zlib").crc32(query.encode()))
    decades = [geo.decade_of(r["date"]) for r in rows]
    counts = {}
    for d in decades:
        if d:
            counts[d] = counts.get(d, 0) + 1
    places = [geo.countries_in(r["title"] + " " + r["snippet"]) for r in rows]
    ctry = {}
    for p in places:
        for iso, name in p.items():
            c = ctry.setdefault(iso, [name, 0])
            c[1] += 1
    if len(counts) >= 2:
        st.markdown('<div class="ww-head">🕰 WHEN · tap a decade</div>', unsafe_allow_html=True)
        import altair as alt
        import pandas as pd
        df = pd.DataFrame(sorted(counts.items()), columns=["Decade", "Documents"])
        chart = (alt.Chart(df).mark_bar(color="#c8a96e", cornerRadiusTopLeft=2, cornerRadiusTopRight=2)
                 .encode(x=alt.X("Decade:N", sort=None, title=None, axis=alt.Axis(labelAngle=0, labelColor="#b9ab8c")),
                         y=alt.Y("Documents:Q", title=None, axis=None), tooltip=["Decade", "Documents"])
                 .properties(height=60).configure_view(strokeWidth=0).configure(background="transparent"))
        st.altair_chart(chart, width="stretch")
        pick = st.pills("Decade", [f"{d} ({n})" for d, n in sorted(counts.items())], key=f"dec-{fkey}",
                        label_visibility="collapsed")
        if pick:
            want = pick.split(" ")[0]
            rows = [r for r, d in zip(rows, decades) if d == want]
            places = [p for p, d in zip(places, decades) if d == want]
    if ctry:
        top = sorted(ctry.items(), key=lambda kv: -kv[1][1])
        st.markdown(f'<div class="ww-head">🌍 WHERE · {len(ctry)} countr{"y" if len(ctry) == 1 else "ies"} named · tap one</div>',
                    unsafe_allow_html=True)
        pickc = st.pills("Country", [f"{v[0]} ({v[1]})" for _iso, v in top[:10]], key=f"cty-{fkey}",
                         label_visibility="collapsed")
        with st.expander("Show the map"):
            try:
                import plotly.graph_objects as go
                fig = go.Figure(go.Choropleth(
                    locations=[iso for iso, _v in top], z=[v[1] for _iso, v in top], text=[v[0] for _iso, v in top],
                    colorscale=[[0, "#4a3d22"], [1, "#e8c77a"]], showscale=False, marker_line_color="#0d0d0d",
                    marker_line_width=0.5, hovertemplate="%{text}: %{z} document(s)<extra></extra>"))
                fig.update_geos(showframe=False, showcoastlines=False, showcountries=True, countrycolor="#2a2a2a",
                                landcolor="#1c1c1c", bgcolor="rgba(0,0,0,0)", projection_type="natural earth")
                fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=260, paper_bgcolor="rgba(0,0,0,0)",
                                  dragmode=False)
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False, "scrollZoom": False})
            except Exception:
                st.caption("The map couldn't be drawn just now.")
            st.caption("Based on country and city names in each result's title and summary.")
        if pickc:
            name = pickc.rsplit(" (", 1)[0]
            rows = [r for r, p in zip(rows, places) if name in p.values()]
    return rows


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def cached_fresh(v=APP_CODE_VERSION):
    out = {}
    for name, fn in (("FBI Vault · recently added", extras.fbi_recent),
                     ("National Security Archive · newest postings", extras.gwu_recent)):
        try:
            out[name] = fn()
        except Exception:
            out[name] = []
    return out


def fresh_releases():
    fresh = cached_fresh(APP_CODE_VERSION)
    if not any(fresh.values()):
        return
    with st.expander("🆕 Newly released files"):
        for name, items in fresh.items():
            if not items:
                continue
            st.markdown(f'<div class="exp-sub">{html.escape(name.upper())}</div>', unsafe_allow_html=True)
            rows = "".join(f'<a class="exp-link" href="{html.escape(i["url"])}" target="_blank">{html.escape(i["title"][:110])}'
                           + (f' · {html.escape(i["date"])}' if i.get("date") else "") + " ↗</a>" for i in items)
            st.markdown(f'<div class="exp-links">{rows}</div>', unsafe_allow_html=True)


NARA_HIGHLIGHTS = [
    ("🎯", "The JFK files", "CIA, FBI and Warren Commission files, released as recently as 2025.", "Lee Harvey Oswald",
     ["Kennedy motorcade Dallas photograph", "Lee Harvey Oswald photograph", "John F. Kennedy photograph"]),
    ("📼", "Nixon's tapes", "Thousands of hours Nixon secretly taped in the White House.", "Nixon White House tapes",
     ["Nixon Oval Office photograph", "President Nixon photograph", "Nixon White House tapes"]),
    ("📄", "Pentagon Papers", "The secret Vietnam War history, fully declassified in 2011.", "Pentagon Papers",
     ["Vietnam War photograph", "Vietnam soldiers helicopter photograph", "Pentagon Papers"]),
    ("🕊", "RFK & MLK files", "Assassination records opened in 2025.", "Robert F. Kennedy assassination",
     ["Robert F. Kennedy photograph", "Martin Luther King photograph", "Robert F. Kennedy assassination"]),
    ("🛸", "UFO records", "The government UFO records Congress ordered gathered.", "unidentified anomalous phenomena",
     ["unidentified flying object photograph", "Project Blue Book", "unidentified anomalous phenomena"]),
    ("🎖", "World War II", "Military files and captured German records.", "captured German records",
     ["World War II photograph", "D-Day Normandy photograph", "captured German records"]),
]


@st.cache_data(ttl=24 * 3600, show_spinner=False, max_entries=10)
def cached_nara_samples(v=APP_CODE_VERSION):
    """One live photo per highlight tile, straight from the National Archives. Missing ones are just left out."""
    from concurrent.futures import ThreadPoolExecutor

    def one(queries):
        fallback = None
        for qq in queries:
            try:
                rows = [r for r in sources.search_nara(qq, limit=25, online_first=False) if r.get("image")]
            except Exception:
                continue
            rows.sort(key=lambda r: not r.get("photo"))          # real photographs before scanned paperwork
            for r in rows[:6]:
                ok = sources.image_is_interesting(r["image"])    # skip blank folder covers and empty pages
                if ok is None and fallback is None:
                    fallback = r                                 # couldn't check it: keep as a backup
                if ok:
                    return {"img": r["image"], "title": r["title"], "url": r["url"], "date": r.get("date", "")}
        if fallback:
            r = fallback
            return {"img": r["image"], "title": r["title"], "url": r["url"], "date": r.get("date", "")}
        return None
    with ThreadPoolExecutor(6) as ex:
        return list(ex.map(one, [h[4] for h in NARA_HIGHLIGHTS]))


@st.cache_data(ttl=6 * 3600, show_spinner=False, max_entries=60)
def cached_nara(q, v=APP_CODE_VERSION):
    return sources.search_nara(q, limit=15)


def _nara_go(q):
    ss.nara_q = q


def nara_box():
    """The National Archives in its own spotlight box, with its own search."""
    if not sources.NARA_ON:
        return
    with st.container(border=True, key="nara-box"):
        st.markdown('<div class="nara-kicker">🏛 THE NATIONAL ARCHIVES</div>'
                    '<div class="nara-title">The nation’s attic: 13 billion pages and counting</div>'
                    '<div class="intro">Washington’s official keeper of government records, from the Constitution '
                    'to the JFK files. Search it on its own here.</div>', unsafe_allow_html=True)
        with st.form("nara-form", border=False):
            nq = st.text_input("Search the National Archives", value=ss.get("nara_q", ""), label_visibility="collapsed",
                               placeholder="Search the National Archives…")
            if st.form_submit_button("🏛 Search the National Archives", width="stretch"):
                ss.nara_q = sources.normalize_query(nq)
        if not ss.get("nara_q"):
            st.markdown('<div class="exp-sub">WHAT’S INSIDE · tap one</div>', unsafe_allow_html=True)
            try:
                samples = cached_nara_samples(APP_CODE_VERSION)
            except Exception:
                samples = [None] * len(NARA_HIGHLIGHTS)
            with st.container(horizontal=True, wrap=True, gap="small", key="nara-tiles"):
                for i, (icon, name, blurb, q, _qs) in enumerate(NARA_HIGHLIGHTS):
                    smp = samples[i] if i < len(samples) else None
                    with st.container(width=140, gap=None, key=f"nara-cell-{i}"):
                        if smp:
                            yr = f" · {smp['date']}" if smp.get("date") else ""
                            st.markdown(f'<a class="nara-photo" href="{html.escape(smp["url"])}" target="_blank" '
                                        f'title="{html.escape(smp["title"])}"><img src="{html.escape(smp["img"])}" '
                                        f'alt="" loading="lazy"><span>📷 {html.escape(smp["title"][:60])}{yr}</span></a>',
                                        unsafe_allow_html=True)
                        st.button(f"{icon}  **{name}**\n\n{blurb}", key=f"nara-tile-{i}", on_click=_nara_go,
                                  args=(q,), width="stretch", wrap=True)
            return
        q = ss.nara_q
        nara_err = ""
        with st.spinner("Searching the National Archives…"):
            try:
                rows = cached_nara(q, APP_CODE_VERSION)
            except Exception as e:
                rows, nara_err = None, f"{type(e).__name__}: {str(e)[:400]}"
        top = st.columns([4, 1], vertical_alignment="center")
        top[0].markdown(f'<div class="sect">NATIONAL ARCHIVES · “{html.escape(q)}”'
                        f'{" · " + str(len(rows)) if rows is not None else ""}</div>', unsafe_allow_html=True)
        top[1].button("✕ Clear", key="nara-clear", on_click=lambda: ss.pop("nara_q", None), type="tertiary")
        if rows is None:
            st.info("The National Archives' search service isn't answering the app right now, so this search "
                    "opens on their own website instead.")
            st.link_button(f"🏛 Search “{q}” on the National Archives website",
                           "https://catalog.archives.gov/search?q=" + urllib.parse.quote(q), type="primary",
                           width="stretch")
            if nara_err:
                with st.expander("Details for troubleshooting"):
                    st.caption(nara_err)
            return
        if not rows:
            st.caption("Nothing came back. Try fewer or different words.")
        online = sum(1 for r in rows if r.get("online"))
        if rows:
            st.caption(f"{online} of {len(rows)} have the document itself online; the rest are catalog entries "
                       "(the record exists, but you'd request it from the Archives).")
        for i, r in enumerate(rows):
            render_result(r, f"na{i}", query=q)
        st.link_button(f"See everything on the National Archives site for “{q}”",
                       "https://catalog.archives.gov/search?q=" + urllib.parse.quote(q), width="stretch")

def _fav_row(f, i):
    with st.container(horizontal=True, vertical_alignment="center", gap="small", key=f"fav-row-{i}"):
        meta = " · ".join(x for x in (f.get("source"), f.get("date")) if x)
        st.markdown(f'<div class="fav-t"><a href="{html.escape(f["url"])}" target="_blank">'
                    f'{html.escape(f.get("title") or f["url"])}</a><span>{html.escape(meta)}</span></div>',
                    unsafe_allow_html=True)
        if f.get("ident"):
            st.button("🕵", key=f"fav-open-{i}", on_click=open_dossier, args=(f["ident"],), type="tertiary",
                      help="Open the dossier")
        st.button("✕", key=f"fav-del-{i}", on_click=toggle_fav, args=(f,), type="tertiary", help="Remove")


def saved_files():
    if not ss.favs:
        return
    with st.container(border=True, key="favbox"):
        st.markdown(f'<div class="fav-head">⭐ MY SAVED FILES · {len(ss.favs)}</div>', unsafe_allow_html=True)
        for i, f in enumerate(ss.favs[:4]):
            _fav_row(f, i)
        if len(ss.favs) > 4:
            with st.expander(f"Show all {len(ss.favs)}"):
                for i, f in enumerate(ss.favs[4:], start=4):
                    _fav_row(f, i)
        if ss.get("fav_storage") is False:
            st.caption("This browser won't let the app keep files (private mode?), so this list lasts only until you close the page.")
        else:
            st.caption("Saved on this device only.")


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
        go = st.form_submit_button("Search all archives", type="primary", width="stretch")

    with st.container(key="popular"):
        st.markdown('<div class="pop-label">Popular searches</div>', unsafe_allow_html=True)
        st.pills("Try", QUICK, key="quick", on_change=_use_quick, label_visibility="collapsed")
    q = ss.qbox
    if ss.pop("run_quick", False):
        go = True

    ss.setdefault("chosen", ALL)
    st.markdown(f'<div class="which">Searching {len(ss.chosen)} archives at once · CIA, FBI, NSA, State Dept and more</div>',
                unsafe_allow_html=True)
    with st.expander("See or change which archives"):
        chosen = st.pills("Archives", ALL, selection_mode="multi", default=ss.chosen, label_visibility="collapsed")
        if chosen is not None and list(chosen) != list(ss.chosen):
            ss.chosen = list(chosen)
            st.rerun()
    chosen = ss.chosen
    saved_files()

    if go and q.strip():
        ss.query = sources.normalize_query(q)
        ss.open_doc = None
        with st.spinner(f"Searching {len(chosen)} archives at once…"):
            ss.results, ss.status = cached_search(ss.query, tuple(chosen), APP_CODE_VERSION)

    # ── Deep dives: tiles on the empty front page ──────────────────────────────
    if not ss.status:
        on_this_day_card()
        st.markdown('<div class="sect">DEEP DIVES · tap a topic</div>', unsafe_allow_html=True)
        topic_tiles("home", with_ancient=True)
        nara_box()

    # ── Results ──────────────────────────────────────────────────────────────────
    results, status = ss.results, ss.status
    st.markdown('<div id="results-anchor"></div>', unsafe_allow_html=True)
    if status:
        show_trail("res")
        if ss.pop("scroll_results", False):
            _scroll("#results-anchor")
        st.button("🏠  Back to home", key="home-top", on_click=_go_home, width="stretch")
        ok = [f"{n} {c}" for n, c in status.items() if isinstance(c, int)]
        bad = [n for n, c in status.items() if not isinstance(c, int)]
        st.caption(f"**{len(results)} results** for “{ss.query}” · " + " · ".join(ok)
                   + (f"  \n⚠️ No answer from: {', '.join(bad)}" if bad else ""))

        explainer_card(explainers.find_program(ss.query) or explainers.find_event(ss.query), "res")
        have = sorted({r["source"] for r in results})
        only = st.pills("Show", ["All"] + have, default="All", label_visibility="collapsed") or "All"
        shown = [r for r in results if only == "All" or r["source"] == only]
        shown = when_where(shown, ss.query)

        if not shown:
            st.info("Nothing came back. Try fewer or different words, or one of the browser links below.")

        for i, r in enumerate(shown[:80]):
            render_result(r, f"r{i}")
        st.button("🏠  Back to home", key="home-bottom", on_click=_go_home, width="stretch")

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
    links = [b for b in BROWSER_ONLY if not (b[0].startswith("National Archives") and sources.NARA_ON)]
    for j, (name, tpl, home) in enumerate(links):
        c[j % 2].link_button(name, tpl.replace("{q}", term) if term else home, width="stretch")
    st.caption("🌐 **Site not in English?** iPhone Safari: tap **aA** in the address bar, then **Translate to English**. "
               "Chrome: tap the translate icon in the address bar.")


# ── Explore: browse by topic ──────────────────────────────────────────────────
with tab_explore:
    st.markdown('<div class="intro">Not sure what to search for? Pick a topic. You get hand-picked '
                'documents (checked against the source) plus fresh finds from the CIA files.</div>',
                unsafe_allow_html=True)
    fresh_releases()
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
            if st.button(f"Search all {len(ALL)} archives for “{main_q}”", key=f"exall{name}", width="stretch"):
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
                'These are real ones, and every quote comes from the scholars who published them. The originals are '
                'in ancient scripts (cuneiform, hieratic, Latin cursive) that no translation app can read, so the '
                'source pages often show only the original or catalog details.</div>', unsafe_allow_html=True)
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
            + (f'<div class="anc-lang">Original: {html.escape(item["lang"])}'
               f'{" · English translation by the scholars who published it" if item["quote"] else ""}</div>'
               if item.get("lang") else "") +
            f'<a class="anc-src" href="{html.escape(item["url"])}" target="_blank">{html.escape(item["source"])} ↗</a></div>',
            unsafe_allow_html=True)
    if st.button("🏺 Show more ancient tablets from the Met Museum", key="metmore", width="stretch"):
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
        if st.form_submit_button("Search company documents", type="primary", width="stretch"):
            ss.corp_q = sources.normalize_query(cq)
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
                       width="stretch")
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
    if st.button("Run check", width="stretch"):
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
        with st.spinner("Checking the National Archives…"):
            if not sources.NARA_ON:
                st.write("**National Archives (own box)** — ⚠️ no key found in Secrets")
            else:
                try:
                    st.write(f"**National Archives (own box)** — ✅ {len(sources.search_nara('Oswald', 5))} results")
                except Exception as e:
                    st.write(f"**National Archives (own box)** — ❌ {type(e).__name__}: {str(e)[:80]}")
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

# ── Before / After: redactions removed (trial section) ─────────────────────────
@st.cache_data(ttl=30 * 24 * 3600, show_spinner=False, max_entries=10)
def cached_reveal(key, v=APP_CODE_VERSION):
    case = next(c for c in redactions.CASES if c["key"] == key)
    return redactions.find_reveal(case)


st.divider()
st.markdown('<div class="ba-head">⬛ BEFORE / AFTER</div>'
            '<div class="intro">The same secret document, released twice: first with black boxes, then again in '
            'March 2025 with them lifted. Tap the page to declassify it.</div>', unsafe_allow_html=True)
labels = {c["short"]: c for c in redactions.CASES}
pick = st.pills("Document", list(labels), default=list(labels)[0], key="ba-pick", label_visibility="collapsed")
case = labels.get(pick) or redactions.CASES[0]
st.markdown(f'<div class="dos-title">{html.escape(case["title"])}</div>'
            f'<div class="meta">{html.escape(case["when"])} · JFK record {html.escape(case["record"])}</div>',
            unsafe_allow_html=True)
with st.spinner("Pulling both versions from the National Archives…"):
    try:
        rv = cached_reveal(case["key"], APP_CODE_VERSION)
    except Exception:
        rv = None
if not rv:
    st.caption("Couldn't load both versions from the National Archives just now. Try again in a minute.")
else:
    revealed = st.session_state.get(f"ba-show-{case['key']}", False)
    label = "🔒 Tap to declassify" if not revealed else "↩ Show the censored version"
    if st.button(label, key=f"ba-btn-{case['key']}", type="primary" if not revealed else "secondary", width="stretch"):
        st.session_state[f"ba-show-{case['key']}"] = not revealed
        st.rerun()
    tag = ("DECLASSIFIED · March 2025 release" if revealed else "CENSORED · earlier release")
    st.markdown(f'<div class="ba-tag {"open" if revealed else "shut"}">{tag} · page {rv["page"]} of {rv["pages"]}</div>',
                unsafe_allow_html=True)
    st.image(rv["after"] if revealed else rv["before"], width="stretch")
    if rv["drop"] < 0.002:
        st.caption("The two versions of this page look nearly identical; the changes may be small, like a few names.")
    st.markdown(f'<div class="ba-sub">WHAT IT IS</div><div class="ba-text">{html.escape(case["what"])}</div>'
                f'<div class="ba-sub">WHY IT WAS SECRET</div><div class="ba-text">{html.escape(case["why"])}</div>'
                f'<div class="links"><a href="{html.escape(rv["old"])}" target="_blank">📄 Censored version ↗</a> '
                f'<a href="{html.escape(rv["new"])}" target="_blank">📄 2025 version ↗</a> '
                f'<a href="{redactions.NSA_POST}" target="_blank">National Security Archive analysis ↗</a></div>',
                unsafe_allow_html=True)

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
    tm[j % 2].link_button(label, url, width="stretch")
st.caption("Tip: every result above also has a 🕰 Saved copy link, and Find my words inside uses a saved "
           "copy automatically when a document has been taken down.")
