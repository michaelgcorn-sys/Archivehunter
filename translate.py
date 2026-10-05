"""
Translation, with the service chosen by a setting, not by code.

To switch on (or swap) a translator, add ONE of these to the app's private Secrets:
    DEEPL_API_KEY = "..."            # DeepL (free plan keys end in ":fx")
    GOOGLE_TRANSLATE_KEY = "..."     # Google Cloud Translation v2
    AZURE_TRANSLATOR_KEY = "..."     # Microsoft Azure Translator
    AZURE_TRANSLATOR_REGION = "eastus"
Optionally force one when several keys exist:
    TRANSLATE_PROVIDER = "deepl" | "google" | "azure"

Everything else in the app calls translate(text) and never knows which service answered,
so moving to a bigger plan or a different company for the public launch is a settings change.
"""

import os
import re

MODULE_VERSION = 56   # keep in step with APP_CODE_VERSION in app.py

import requests

TIMEOUT = 25


def _secret(name):
    try:
        import streamlit as st
        v = st.secrets.get(name)
        if v:
            return str(v).strip()
    except Exception:
        pass
    return os.environ.get(name, "").strip()


# ── Providers: each takes (text, target) and returns (translated text, detected source language) ──

def _deepl(text, target):
    key = _secret("DEEPL_API_KEY")
    host = "api-free.deepl.com" if key.endswith(":fx") else "api.deepl.com"
    r = requests.post(f"https://{host}/v2/translate", headers={"Authorization": f"DeepL-Auth-Key {key}"},
                      data={"text": text, "target_lang": "EN-US" if target == "en" else target.upper()},
                      timeout=TIMEOUT)
    r.raise_for_status()
    t = r.json()["translations"][0]
    return t["text"], t.get("detected_source_language", "").lower()


def _google(text, target):
    r = requests.post("https://translation.googleapis.com/language/translate/v2",
                      params={"key": _secret("GOOGLE_TRANSLATE_KEY")},
                      data={"q": text, "target": target, "format": "text"}, timeout=TIMEOUT)
    r.raise_for_status()
    t = r.json()["data"]["translations"][0]
    return t["translatedText"], t.get("detectedSourceLanguage", "")


def _azure(text, target):
    r = requests.post("https://api.cognitive.microsofttranslator.com/translate",
                      params={"api-version": "3.0", "to": target},
                      headers={"Ocp-Apim-Subscription-Key": _secret("AZURE_TRANSLATOR_KEY"),
                               "Ocp-Apim-Subscription-Region": _secret("AZURE_TRANSLATOR_REGION") or "global"},
                      json=[{"text": text}], timeout=TIMEOUT)
    r.raise_for_status()
    t = r.json()[0]
    return t["translations"][0]["text"], t.get("detectedLanguage", {}).get("language", "")


PROVIDERS = {          # name: (key that switches it on, function, label shown to users)
    "deepl": ("DEEPL_API_KEY", _deepl, "DeepL"),
    "google": ("GOOGLE_TRANSLATE_KEY", _google, "Google Translate"),
    "azure": ("AZURE_TRANSLATOR_KEY", _azure, "Microsoft Translator"),
}


def active_provider():
    """Name of the translator in use, or None when no key is set."""
    forced = _secret("TRANSLATE_PROVIDER").lower()
    if forced in PROVIDERS and _secret(PROVIDERS[forced][0]):
        return forced
    for name, (key, _fn, _label) in PROVIDERS.items():
        if _secret(key):
            return name
    return None


def provider_label():
    p = active_provider()
    return PROVIDERS[p][2] if p else None


MAX_CHARS = 4500     # keeps each request (and monthly usage) small


def translate(text, target="en"):
    """Returns (translated text, detected language). Raises if no translator is configured."""
    p = active_provider()
    if not p:
        raise RuntimeError("no translator configured")
    return PROVIDERS[p][1](text[:MAX_CHARS], target)


# ── Is this text English? (no service needed) ────────────────────────────────
_EN = set("the of and to in is that for it as was with be by on not this are from or have an which "
          "at but were has been their they will would all its".split())


def looks_foreign(text):
    """True when text is clearly not English: few common English words, or mostly non-Latin letters."""
    words = re.findall(r"[^\W\d_]+", (text or "").lower())
    if len(words) < 8:
        return False
    latin = sum(bool(re.fullmatch(r"[a-z]+", w)) for w in words) / len(words)
    if latin < 0.5:                       # Cyrillic, Chinese, Arabic...
        return True
    return sum(w in _EN for w in words) / len(words) < 0.04
