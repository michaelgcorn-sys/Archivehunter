"""Open the app like a visitor and press Streamlit's wake-up button if it's asleep."""
import subprocess
import sys
import time

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "playwright"], check=True)
subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"], check=True,
               stdout=subprocess.DEVNULL)
from playwright.sync_api import sync_playwright  # noqa: E402

URL = sys.argv[1] if len(sys.argv) > 1 else "https://archivehunter.streamlit.app/"


def note(m):
    print("::notice::" + m[:900], flush=True)


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.goto(URL, timeout=90000)
    pg.wait_for_timeout(8000)
    note(f"landed on {pg.url} | text: {pg.inner_text('body')[:300]!r}")
    btn = pg.get_by_role("button", name="Yes, get this app back up!")
    if btn.count():
        btn.click()
        note("app was asleep: pressed the wake-up button")
    t0 = time.time()
    ok = False
    while time.time() - t0 < 600:            # wait up to 10 minutes for the app itself to appear
        for fr in pg.frames:
            try:
                if fr.locator("text=Archive Hunter").count():
                    ok = True
                    break
            except Exception:
                pass
        if ok:
            break
        pg.wait_for_timeout(5000)
    note(f"app {'is UP' if ok else 'did not finish loading'} after {time.time() - t0:.0f}s")
    if ok:
        pg.wait_for_timeout(40000)            # let the home page finish loading so its data is cached
    b.close()
