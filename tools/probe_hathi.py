import re
import requests
ID = "pur1.32754081232310"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
for url in [f"https://babel.hathitrust.org/cgi/ssd?id={ID};seq=42",
            f"https://babel.hathitrust.org/cgi/pt?id={ID}&seq=42",
            f"https://babel.hathitrust.org/cgi/imgsrv/download/plaintext?id={ID}&seq=42",
            f"https://babel.hathitrust.org/cgi/imgsrv/download/pdf?id={ID}&seq=42&attachment=0",
            f"https://babel.hathitrust.org/cgi/htd/volume/pageocr/{ID}/42"]:
    try:
        r = requests.get(url, headers=UA, timeout=40)
        print("::notice::" + url.split("/cgi/")[1][:70] + " -> " + str(r.status_code) + " "
              + r.headers.get("content-type", "")[:40] + " len=" + str(len(r.content)) + " | "
              + re.sub(r"\s+", " ", r.text[:260] if "text" in r.headers.get("content-type", "") else ""), flush=True)
    except Exception as e:
        print("::notice::" + url + " error " + type(e).__name__, flush=True)
