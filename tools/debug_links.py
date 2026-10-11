"""One-off: show how the Nixon Library links transcripts (prints GitHub annotations)."""
import re
import requests
UA = {"User-Agent": "ArchiveHunter-index-builder/1.0"}
WS = re.compile(r"\s+")
for url in ["https://www.nixonlibrary.gov/watergate-special-prosecution-force-transcripts",
            "https://www.nixonlibrary.gov/white-house-tapes/472/conversation-472-004"]:
    h = requests.get(url, headers=UA, timeout=60).text
    name = url.rsplit("/", 1)[-1]
    hrefs = sorted(set(re.findall(r'href="([^"#]+)"', h)))
    keep = [x for x in hrefs if re.search(r"files|pdf|transcript|472|e-?25", x, re.I)]
    print("::notice::" + name + " hrefs=" + str(len(hrefs)) + " keep=" + str(keep[:25]))
    i = h.find("472-004")
    print("::notice::" + name + " around472=" + WS.sub(" ", h[max(0, i - 700):i + 500])[:1100])
    j = h.lower().find("transcript", max(0, h.lower().find("<main")))
    print("::notice::" + name + " aroundTranscript=" + WS.sub(" ", h[max(0, j - 300):j + 500])[:800])
