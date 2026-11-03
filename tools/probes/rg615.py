"""How much of the National Archives' UAP collection (Record Group 615) is in the online catalog?"""
import requests

H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Content-Type": "application/json"}
U = "https://catalog.archives.gov/proxy/v3/records/search"
for label, params in [("RG 615 (recordGroupNumber)", {"recordGroupNumber": "615", "limit": 5}),
                      ("q=Record Group 615", {"q": '"Record Group 615"', "limit": 5}),
                      ("q=unidentified anomalous phenomena", {"q": "unidentified anomalous phenomena", "limit": 5})]:
    try:
        j = requests.get(U, params=params, headers=H, timeout=40).json()
        hits = j.get("body", {}).get("hits", {})
        tot = hits.get("total", {})
        titles = [h.get("_source", {}).get("record", {}).get("title", "")[:70] for h in hits.get("hits", [])[:5]]
        print(f"::notice::{label}: total {tot} · {titles}", flush=True)
    except Exception as e:
        print(f"::notice::{label}: ERROR {e}", flush=True)
