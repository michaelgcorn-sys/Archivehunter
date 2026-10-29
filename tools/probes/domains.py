"""Check which domain names are registered (RDAP: 404 = not registered, likely available)."""
import requests

NAMES = ["archivehunter", "archive-hunter", "thearchivehunter", "archivehunters", "exhibitaarchive", "exhibita",
         "declassifiedhunter", "declassified", "huntthearchive", "archivehunt"]
TLDS = ["com", "io", "org", "net", "co", "news", "app"]
H = {"Accept": "application/rdap+json", "User-Agent": "ArchiveHunter domain check"}
for n in NAMES:
    row = []
    for t in TLDS:
        d = f"{n}.{t}"
        try:
            r = requests.get(f"https://rdap.org/domain/{d}", headers=H, timeout=20, allow_redirects=True)
            s = "TAKEN" if r.status_code == 200 else ("free?" if r.status_code == 404 else f"?{r.status_code}")
        except Exception as e:
            s = f"err:{type(e).__name__}"
        row.append(f"{t}={s}")
    print(f"::notice::{n}: " + "  ".join(row), flush=True)
for app in ["archivehunter", "archive-hunter"]:
    try:
        r = requests.get(f"https://{app}.fly.dev", timeout=15)
        print(f"::notice::fly.dev {app}: responds {r.status_code} (probably taken)", flush=True)
    except Exception as e:
        print(f"::notice::fly.dev {app}: no response ({type(e).__name__}) - likely free", flush=True)
