import json
import os
import re
import sys

sys.path.insert(0, os.getcwd())
import requests  # noqa: E402
import sources as S  # noqa: E402


def note(m):
    print("::notice::" + m[:1000], flush=True)


out = {"cia": [], "nara": []}
UA = {"User-Agent": "ArchiveHunter/1.0"}
for q in ['title:("flying saucer")', 'title:("flying saucers")', 'title:("unidentified flying")',
          'title:(ufo) AND title:(sighting)', 'title:("unidentified object")', 'title:("strange object")',
          'title:(saucer) AND title:(observed)']:
    try:
        r = requests.get("https://archive.org/advancedsearch.php", headers=UA, timeout=40,
                         params={"q": f"collection:ciareadingroom AND {q}", "fl[]": ["identifier", "title", "date"],
                                 "rows": 60, "output": "json"})
        docs = r.json()["response"]["docs"]
        for d in docs:
            out["cia"].append({"id": d["identifier"], "title": d.get("title"), "date": d.get("date")})
        note(f"CIA {q}: {len(docs)}")
    except Exception as e:
        note(f"CIA {q} ERROR {e}")
seen, uniq = set(), []
for d in out["cia"]:
    if d["id"] not in seen:
        seen.add(d["id"])
        uniq.append(d)
out["cia"] = uniq
for d in out["cia"][:150]:
    try:
        t = requests.get(f"https://archive.org/download/{d['id']}/{d['id']}_djvu.txt", headers=UA, timeout=30)
        txt = re.sub(r"\s+", " ", t.text)[:1800] if t.status_code == 200 else ""
        d["text"] = txt
        d["quality"] = round(S.text_quality(txt), 2) if txt else 0
    except Exception:
        d["text"] = ""
for q in ["Project Blue Book sketch", "Project Blue Book photograph unidentified", "unidentified flying object photograph",
          "UFO sighting witness statement", "flying saucer photograph 1952"]:
    try:
        rows = S.search_nara(q, limit=25, online_first=False)
        for r in rows:
            out["nara"].append({"q": q, "title": r["title"], "url": r["url"], "date": r.get("date"),
                                "image": r.get("image"), "photo": r.get("photo"),
                                "snippet": r.get("snippet", "")[:300]})
        note(f"NARA {q}: {len(rows)} rows, {sum(1 for r in rows if r.get('image'))} with image")
    except Exception as e:
        note(f"NARA {q} ERROR {e}")
os.makedirs("data/probe", exist_ok=True)
json.dump(out, open("data/probe/ufo_candidates.json", "w"), indent=0)
note(f"saved {len(out['cia'])} CIA, {len(out['nara'])} NARA")
