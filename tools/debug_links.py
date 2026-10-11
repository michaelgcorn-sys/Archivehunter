"""One-off: find how the Nixon Library's embedded transcript media resolve (prints GitHub annotations)."""
import re
import requests
UA = {"User-Agent": "ArchiveHunter-index-builder/1.0", "Accept": "application/vnd.api+json, application/json, */*"}
B = "https://www.nixonlibrary.gov"
U = "2291cc57-f35c-4394-8c71-d8e2a1bcd462"
listing = requests.get(B + "/watergate-special-prosecution-force-transcripts", headers=UA, timeout=60).text
print("::notice::uuids on listing=" + str(len(set(re.findall(r'data-entity-uuid="([0-9a-f-]{36})"', listing)))))
for path in ["/jsonapi", "/jsonapi/media/document/" + U, "/jsonapi/media/audio/" + U, "/jsonapi/media/file/" + U,
             "/jsonapi/media/remote_video/" + U, "/media/oembed?uuid=" + U]:
    try:
        r = requests.get(B + path, headers=UA, timeout=60)
        body = re.sub(r"\s+", " ", r.text)
        types = sorted(set(re.findall(r'"(media--[a-z_]+)"', body)))
        files = re.findall(r'"(?:url|href)":\s*"([^"]+\.(?:pdf|mp3|txt|doc|docx)[^"]*)"', r.text)
        print("::notice::" + path[:60] + " -> " + str(r.status_code) + " " + r.headers.get("content-type", "")[:40]
              + " types=" + str(types[:12]) + " files=" + str(files[:4]) + " body=" + body[:300])
    except Exception as e:
        print("::notice::" + path + " error " + type(e).__name__)
