"""One-off: render the transcript listing in a real browser and report what the embedded media become."""
import re
from playwright.sync_api import sync_playwright
B = "https://www.nixonlibrary.gov"
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(user_agent="Mozilla/5.0 ArchiveHunter-index-builder/1.0")
    pg.goto(B + "/watergate-special-prosecution-force-transcripts", wait_until="networkidle", timeout=90000)
    pg.wait_for_timeout(4000)
    links = pg.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    media = pg.eval_on_selector_all("audio source, audio, video source, iframe, embed, object",
                                    "els => els.map(e => e.src || e.data || '')")
    keep = sorted(set(l for l in links if re.search(r"\.(pdf|mp3|txt|docx?)\b|files/", l, re.I)))
    print("::notice::rendered links=" + str(len(links)) + " files=" + str(keep[:20]))
    print("::notice::media=" + str(media[:12]))
    html = pg.content()
    i = html.find("472-004")
    print("::notice::around=" + re.sub(r"\s+", " ", html[max(0, i - 900):i + 300])[:1200])
    b.close()
