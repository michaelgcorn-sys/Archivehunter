import re
import requests


def note(m):
    print("::notice::" + m[:1000], flush=True)


UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
for url in ["https://www.war.gov/UFO/", "https://www.war.gov/ufo/",
            "https://www.war.gov/medialink/ufo/061226/release_03/documents/DOW-UAP-D077_Unresolved-Case-Analysis-Update_Western-United-States-Event.pdf"]:
    try:
        r = requests.get(url, headers=UA, timeout=40)
        links = sorted(set(re.findall(r'(?:href|src)="([^"#]+)"', r.text))) if "html" in r.headers.get("content-type", "") else []
        media = [l for l in links if re.search(r"medialink|\.pdf|\.mp4|\.jpg|\.png|release", l, re.I)]
        note(f"{url[:90]} -> {r.status_code} {r.headers.get('content-type','')[:30]} {len(r.content)} bytes; links {len(links)}; media {len(media)}: {media[:25]}")
        if "html" in r.headers.get("content-type", ""):
            note("page text: " + re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))[:900])
    except Exception as e:
        note(f"{url} ERROR {type(e).__name__}: {e}")
