"""Pick which Nixon conversations to subtitle in bulk, from the tape-log index.

Usage: python tools/plan_subtitles.py <topic> [max]
Prints a JSON list of conversation numbers (for a GitHub Actions matrix): conversations whose log mentions the
topic, whose audio is online, that don't have subtitles yet, and that are short enough to finish in one job.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import sources as S  # noqa: E402

TOPICS = {"jewish": r"\bJew(?:s|ish|ry)?\b", "watergate": r"\bWatergate\b"}
ONLINE = [(27, 41), (43, 46), (137, 169), (176, 186), (196, 244), (348, 448), (746, 950)]
HEAD = re.compile(r"Conversation\s+No\.?\s*(\d{3})\s*-\s*0*(\d{1,3})(?![\dA-Z])(?!\s*\(cont)")
TIME = re.compile(r"Time:\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*-\s*(\d{1,2}):(\d{2})\s*([ap])", re.I)
MAX_MIN = 200          # longer conversations would not finish inside one 6-hour job


def minutes(h, m, ap):
    return (int(h) % 12 + (12 if ap.lower() == "p" else 0)) * 60 + int(m)


def plan(topic, cap=256):
    pat = re.compile(TOPICS.get(topic, topic), re.I)
    done = set()
    tdir = os.path.join(os.path.dirname(__file__), "..", "data", "transcripts")
    if os.path.isdir(tdir):
        done = {f[:-5] for f in os.listdir(tdir) if f.endswith(".json")}
    picks = []
    for t in S.load_nixon_index()["tapes"]:
        n = int(t["tape"])
        if not any(a <= n <= b for a, b in ONLINE):
            continue
        text, heads = t["text"], list(HEAD.finditer(t["text"]))
        for i, h in enumerate(heads):
            block = text[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
            cid = f"{h.group(1)}-{int(h.group(2)):03d}"
            if cid in done or cid in picks or cid not in t.get("convs", []) or not pat.search(block):
                continue
            tm = TIME.search(block)
            dur = (minutes(*tm.group(4, 5, 6)) - minutes(*tm.group(1, 2, 3))) if tm else None
            if dur is not None and not (1 <= dur <= MAX_MIN):
                continue
            picks.append(cid)
    return picks[:cap]


if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else "jewish"
    cap = int(sys.argv[2]) if len(sys.argv) > 2 else 256
    print(json.dumps(plan(topic, cap)))
