"""Open the Fly.io site like a visitor (phone and laptop), time it, and save screenshots."""
import os
import subprocess
import sys
import time

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "playwright"], check=True)
subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"], check=True,
               stdout=subprocess.DEVNULL)
import requests  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

URL = "https://archivehunter.fly.dev"
t0 = time.time()
r = requests.get(URL + "/_stcore/health", timeout=60)
print(f"::notice::health {r.status_code} {r.text[:20]!r} in {time.time() - t0:.1f}s", flush=True)
os.makedirs("data/probe", exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, vp in [("phone", {"width": 390, "height": 844}), ("laptop", {"width": 1440, "height": 900})]:
        pg = b.new_page(viewport=vp, device_scale_factor=1)
        t0 = time.time()
        pg.goto(URL, timeout=90000)
        pg.wait_for_selector("text=Archive Hunter", timeout=90000)
        first = time.time() - t0
        try:
            pg.wait_for_selector(".ex-hero", timeout=60000)
        except Exception:
            pass
        hero = time.time() - t0
        pg.wait_for_timeout(15000)
        exc = pg.locator("[data-testid='stException']").count()
        pg.screenshot(path=f"data/probe/fly_{name}.png")
        print(f"::notice::{name}: title visible {first:.1f}s, exhibit {hero:.1f}s, errors {exc}", flush=True)
        pg.close()
    b.close()
