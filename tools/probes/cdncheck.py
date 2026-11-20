import requests
for u in ["https://cdn.jsdelivr.net/gh/michaelgcorn-sys/Archivehunter@ufo-files/r08/pdf/DOW-UAP-D191-Air_Intelligence_Information_Report_Texas-1957.pdf",
          "https://raw.githubusercontent.com/michaelgcorn-sys/Archivehunter/ufo-files/r08/thumbs/DOW-UAP-D191-Air_Intelligence_Information_Report_Texas-1957.jpg"]:
    r = requests.get(u, timeout=60)
    print(f"::notice::{r.status_code} {r.headers.get('content-type')} {len(r.content)} {u[-40:]}", flush=True)
