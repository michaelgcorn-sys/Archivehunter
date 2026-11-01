"""Check which domain names are registered (RDAP: 404 = not registered, likely available)."""
import time

import requests

BOOT = requests.get("https://data.iana.org/rdap/dns.json", timeout=20).json()
BASE = {t: svc[1][0] for svc in BOOT["services"] for t in svc[0]}

NAMES = ["eyesonlyfiles", "eyesonlyarchive", "theeyesonly", "geteyesonly", "eyesonlydaily", "burnbagfiles",
         "theburnbagfiles", "blackbarfiles", "redactionhunter", "declassifieddaily", "dailydeclassified",
         "declassifiedtoday", "secretfilesdaily", "thesecretfiles", "opentheFiles", "openthefile", "filehunter",
         "thefilehunter", "dossierhunter", "classifiedhunter", "foiahunter", "thefoiafiles", "archivehunterhq",
         "archivehunterapp", "getarchivehunter", "huntarchives", "declasshunter", "topsecretfiles",
         "topsecretarchive", "unclassifiedfiles", "nowdeclassified", "justdeclassified", "freshlydeclassified",
         "readtheredacted", "behindtheblackbar", "thedeclassifiednews"]
TLDS = ["com"]
H = {"Accept": "application/rdap+json", "User-Agent": "ArchiveHunter domain check"}
LINES = []
for n in NAMES:
    row = []
    for t in TLDS:
        d = f"{n}.{t}"
        try:
            r = requests.get(BASE[t].rstrip("/") + f"/domain/{d}", headers=H, timeout=20, allow_redirects=True)
            time.sleep(0.8)
            s = "TAKEN" if r.status_code == 200 else ("free?" if r.status_code == 404 else f"?{r.status_code}")
        except Exception as e:
            s = f"err:{type(e).__name__}"
        row.append(f"{t}={s}")
    print(f"::notice::{n}: " + "  ".join(row), flush=True)
    LINES.append(f"{n}: " + "  ".join(row))
for app in []:
    try:
        r = requests.get(f"https://{app}.fly.dev", timeout=15)
        print(f"::notice::fly.dev {app}: responds {r.status_code} (probably taken)", flush=True)
    except Exception as e:
        print(f"::notice::fly.dev {app}: no response ({type(e).__name__}) - likely free", flush=True)

import os
os.makedirs("data/probe", exist_ok=True)
open("data/probe/domains.txt", "w").write("\n".join(LINES) + "\n")
