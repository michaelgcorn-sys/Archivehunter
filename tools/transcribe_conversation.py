"""Machine subtitles for one Nixon tape conversation (runs in GitHub Actions, not in the app).

Usage: python tools/transcribe_conversation.py 840-005 [model]
Finds the audio on the conversation's Nixon Library page, runs the open-source Whisper speech
recognizer on it, and writes data/transcripts/<conv>.json (timed segments) for the app to show.
"""
import json
import os
import re
import sys
import time

import requests

BASE = "https://www.nixonlibrary.gov"
UA = {"User-Agent": "ArchiveHunter-transcriber/1.0 (research app; github.com/michaelgcorn-sys/Archivehunter)"}
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "transcripts")


def audio_url(conv):
    tape = conv.split("-")[0]
    page = f"{BASE}/white-house-tapes/{tape}/conversation-{conv}"
    r = requests.get(page, headers=UA, timeout=60)
    r.raise_for_status()
    found = re.findall(r'(?:src|href)="([^"]+\.(?:mp3|m4a|wav|ogg)(?:\?[^"]*)?)"', r.text, re.I)
    if not found:
        raise SystemExit(f"no audio link found on {page}")
    u = found[0]
    return page, (u if u.startswith("http") else BASE + u)


def main():
    conv = sys.argv[1]
    model_name = sys.argv[2] if len(sys.argv) > 2 else "large-v3"
    clean = os.environ.get("CLEAN_AUDIO", "1") == "1"
    page, url = audio_url(conv)
    print("audio:", url, flush=True)
    os.makedirs("/tmp/audio", exist_ok=True)
    path = "/tmp/audio/" + os.path.basename(url.split("?")[0])
    # the Archives' audio server sometimes drops long downloads: retry, resuming where it stopped
    for attempt in range(6):
        have = os.path.getsize(path) if os.path.exists(path) else 0
        hdrs = dict(UA, **({"Range": f"bytes={have}-"} if have else {}))
        try:
            with requests.get(url, headers=hdrs, timeout=300, stream=True) as r:
                if have and r.status_code == 200:          # server ignored the resume request: start over
                    have = 0
                elif r.status_code == 416:                 # already complete
                    break
                r.raise_for_status()
                with open(path, "ab" if have else "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            break
        except (requests.exceptions.ChunkedEncodingError, requests.exceptions.ConnectionError,
                requests.exceptions.ReadTimeout) as e:
            print(f"download interrupted ({type(e).__name__}), retry {attempt + 1}", flush=True)
            time.sleep(10 * (attempt + 1))
    else:
        raise SystemExit("audio download kept failing")
    print("downloaded", os.path.getsize(path) // 1024, "KB", flush=True)

    if clean:     # Nixon tapes: cut rumble and hiss, keep the voice band, even out loud and quiet voices
        import subprocess
        cleaned = path.rsplit(".", 1)[0] + "-clean.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", "16000", "-af",
                        "highpass=f=150,lowpass=f=3800,afftdn=nf=-25,dynaudnorm=f=150:g=15,volume=1.5", cleaned],
                       check=True)
        path = cleaned
        print("cleaned audio", flush=True)

    from faster_whisper import WhisperModel
    t0 = time.time()
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, info = model.transcribe(path, beam_size=5, vad_filter=False, condition_on_previous_text=False,
                                      no_speech_threshold=0.6, log_prob_threshold=-1.0, language="en",
                                      temperature=[0.0, 0.2, 0.4], compression_ratio_threshold=2.2,
                                      initial_prompt="Oval Office conversation, 1973. President Nixon speaking with staff.")
    out = []
    for s in segments:
        out.append({"start": round(s.start, 1), "end": round(s.end, 1), "text": s.text.strip(),
                    "conf": round(s.avg_logprob, 2), "no_speech": round(s.no_speech_prob, 2)})
        if len(out) % 25 == 0:
            print(f"{len(out)} segments, at {s.end / 60:.1f} min", flush=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    meta = {"conv": conv, "page": page, "audio": url, "model": model_name, "cleaned": clean, "seconds": round(info.duration),
            "made": time.strftime("%Y-%m-%d"), "took_min": round((time.time() - t0) / 60, 1)}
    with open(os.path.join(OUT_DIR, f"{conv}.json"), "w") as f:
        json.dump({"meta": meta, "segments": out}, f, ensure_ascii=False, indent=0)
    print("done", meta, flush=True)


if __name__ == "__main__":
    try:
        main()
    except BaseException as e:            # surface the reason as a GitHub annotation (readable via the API)
        import traceback
        tb = traceback.format_exc().strip().splitlines()
        print(f"::error::{type(e).__name__}: {str(e)[:300]} | {' / '.join(tb[-4:])[:600]}", flush=True)
        raise
