import os
import sys
sys.path.insert(0, os.getcwd())
import sources as S  # noqa: E402
a = S.top_secret_pool()
b = S.top_secret_pool()
ua, ub = {r["url"] for r in a}, {r["url"] for r in b}
print(f"::notice::pool A {len(a)} (hot {sum(1 for r in a if r.get('interest',0)>0)}), pool B {len(b)}, overlap {len(ua & ub)}, union {len(ua | ub)}", flush=True)
