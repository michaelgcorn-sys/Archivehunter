"""Time each home-page data loader on a cold start (what the first visitor after a restart waits for)."""
import os
import sys
import time

sys.path.insert(0, os.getcwd())
import sources as S  # noqa: E402


def t(name, fn):
    t0 = time.time()
    try:
        out = fn()
        n = len(out) if hasattr(out, "__len__") else "?"
        print(f"::notice::{name}: {time.time() - t0:.1f}s ({n} items)", flush=True)
    except Exception as e:
        print(f"::notice::{name}: FAILED after {time.time() - t0:.1f}s {type(e).__name__} {str(e)[:120]}", flush=True)


t("UFO records (remote)", lambda: S.load_ufo_records(remote=True))
t("Top Secret pool", S.top_secret_pool)
t("On this day (PDB)", lambda: S.pdb_on_this_day(10, 16))
t("Nixon index", S.load_nixon_index)
t("NARA one search", lambda: S.search_nara("Nixon Oval Office photograph", limit=25, online_first=False))
rows = [r for r in S.search_nara("Lee Harvey Oswald photograph", limit=25, online_first=False) if r.get("image")]
t0 = time.time()
for r in rows[:8]:
    S.image_is_interesting(r["image"])
print(f"::notice::NARA 8 image checks: {time.time() - t0:.1f}s", flush=True)
