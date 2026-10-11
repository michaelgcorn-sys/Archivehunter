import os, re, sys
sys.path.insert(0, os.getcwd())
import requests
import sources as S
def note(m): print("::notice::" + m[:900], flush=True)
for q in ["site:dia.mil FOIA UFO", "site:dia.mil UFO", "site:dia.mil UAP", "site:dia.mil remote viewing", "site:archives.nato.int Berlin"]:
    try:
        eng, hits = S.web_search(q, want=lambda h: ("dia.mil" in h) or ("nato.int" in h))
        on = [h for h, t, s in hits if "dia.mil" in h or "nato.int" in h]
        note(f"{q!r} via {eng}: {len(hits)} hits, {len(on)} on-site: " + " | ".join(f"{t[:50]} <{h[:90]}>" for h, t, s in hits if h in on)[:700])
    except Exception as e:
        note(f"{q!r} ERROR {e}")
for url in ["https://www.dia.mil/FOIA/FOIA-Electronic-Reading-Room/", "https://archives.nato.int/"]:
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=40)
        links = sorted(set(re.findall(r'href="([^"#]+)"', r.text)))
        keep = [l for l in links if re.search(r"FOIA|Reading|FileId|\.pdf|informationobject|search", l, re.I)]
        note(f"{url} -> {r.status_code} {len(r.text)} chars; links {len(links)}; sample: {keep[:30]}")
    except Exception as e:
        note(f"{url} ERROR {type(e).__name__}")
