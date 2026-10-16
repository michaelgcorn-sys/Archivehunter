"""Gather documents marked TOP SECRET ahead of time (runs daily in GitHub Actions), so the app's Top Secret strip
opens instantly instead of searching several archives live (~30 seconds) for the first visitor after a restart.
Writes data/top_secret_pool.json."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import sources as S  # noqa: E402

pool, seen = [], set()
for _ in range(4):                       # each run draws random pages, so a few rounds give a bigger, varied pool
    try:
        for r in S.top_secret_pool():
            if r["url"] not in seen:
                seen.add(r["url"])
                pool.append(r)
    except Exception as e:
        print("round failed:", e, flush=True)
if len(pool) < 20:
    raise SystemExit(f"only {len(pool)} documents; keeping the old file")
out = os.path.join(os.path.dirname(__file__), "..", "data", "top_secret_pool.json")
json.dump({"made": time.strftime("%Y-%m-%d"), "docs": pool}, open(out, "w"), ensure_ascii=False, indent=0)
print(f"::notice::saved {len(pool)} Top Secret documents", flush=True)
