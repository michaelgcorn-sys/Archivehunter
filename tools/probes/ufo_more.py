"""How many more UFO records with pictures/text could the app draw on beyond the war.gov release?"""
import json
import os
import sys

sys.path.insert(0, os.getcwd())
import requests  # noqa: E402
import sources as S  # noqa: E402

UA = {"User-Agent": "ArchiveHunter/1.0"}
out = {}


def note(m):
    print("::notice::" + m[:900], flush=True)


def ia(q, rows=3):
    r = requests.get("https://archive.org/advancedsearch.php", headers=UA, timeout=40,
                     params={"q": q, "fl[]": ["identifier", "title", "mediatype"], "rows": rows, "output": "json"})
    j = r.json()["response"]
    return j["numFound"], [d.get("title") for d in j["docs"]]


for name, q in [("IA Blue Book any", '"project blue book"'),
                ("IA Blue Book texts", '"project blue book" AND mediatype:texts'),
                ("IA bluebook collection", 'collection:projectbluebook'),
                ("IA CIA reading room UFO", 'collection:ciareadingroom AND (UFO OR "flying saucer" OR "unidentified flying")'),
                ("IA FBI vault UFO", '(collection:fbifiles OR collection:fbi-vault) AND (UFO OR "flying saucer" OR "flying disc")'),
                ("IA Blue Book case files", 'title:("blue book") AND title:(case OR sighting)')]:
    try:
        n, sample = ia(q)
        out[name] = {"n": n, "sample": sample}
        note(f"{name}: {n} · e.g. {sample}")
    except Exception as e:
        note(f"{name}: ERROR {e}")

for q in ["Project Blue Book", "unidentified flying object", "unidentified anomalous phenomena", "flying saucer"]:
    try:
        rows = S.search_nara(q, limit=100, online_first=False)
        withimg = sum(1 for r in rows if r.get("image"))
        note(f"NARA '{q}': {len(rows)} rows returned (first 100), {withimg} with images · e.g. {[r['title'][:60] for r in rows[:3]]}")
        out["NARA " + q] = {"rows": len(rows), "img": withimg}
    except Exception as e:
        note(f"NARA {q}: ERROR {e}")
os.makedirs("data/probe", exist_ok=True)
json.dump(out, open("data/probe/ufo_more.json", "w"), indent=1)
