"""
Explainers: plain-English background on a program before the raw documents.

PROGRAMS maps codewords and search terms to the Wikipedia article that explains them. The mapping is
written by hand, so a codeword can never pull up the wrong article. If an article is missing,
the card simply doesn't appear. Text comes from Wikipedia's free summary service and is always
shown labeled as Wikipedia background, with a link to the full article (CC BY-SA).
"""

import re
import urllib.parse

import requests

MODULE_VERSION = 50   # keep in step with APP_CODE_VERSION in app.py

_UA = {"User-Agent": "ArchiveHunter/1.0 (personal research app for declassified records)"}

# term (as it appears in documents or searches) -> (display name, Wikipedia article)
PROGRAMS = {
    "MKULTRA": ("MKUltra", "MKUltra"), "MK-ULTRA": ("MKUltra", "MKUltra"), "MK ULTRA": ("MKUltra", "MKUltra"),
    "MKSEARCH": ("MKUltra", "MKUltra"), "MKNAOMI": ("MKNAOMI", "MKNAOMI"),
    "ARTICHOKE": ("Project Artichoke", "Project Artichoke"),
    "GRILL FLAME": ("the Stargate Project (remote viewing)", "Stargate Project"),
    "STARGATE": ("the Stargate Project (remote viewing)", "Stargate Project"),
    "STAR GATE": ("the Stargate Project (remote viewing)", "Stargate Project"),
    "SUN STREAK": ("the Stargate Project (remote viewing)", "Stargate Project"),
    "CENTER LANE": ("the Stargate Project (remote viewing)", "Stargate Project"),
    "GONDOLA WISH": ("the Stargate Project (remote viewing)", "Stargate Project"),
    "REMOTE VIEWING": ("remote viewing", "Remote viewing"),
    "CORONA": ("the CORONA spy satellite program", "Corona (satellite)"),
    "GAMBIT": ("the GAMBIT spy satellites", "KH-7 Gambit"),
    "HEXAGON": ("the HEXAGON spy satellites", "KH-9 Hexagon"),
    "AQUATONE": ("the U-2 spy plane program", "Lockheed U-2"),
    "IDEALIST": ("the U-2 spy plane program", "Lockheed U-2"),
    "U-2": ("the U-2 spy plane", "Lockheed U-2"),
    "OXCART": ("OXCART, the A-12 spy plane", "Lockheed A-12"),
    "BLACKSHIELD": ("OXCART, the A-12 spy plane", "Lockheed A-12"),
    "TAGBOARD": ("the D-21 spy drone", "Lockheed D-21"),
    "AZORIAN": ("Project Azorian", "Project Azorian"),
    "MHCHAOS": ("Operation CHAOS", "Operation CHAOS"), "OPERATION CHAOS": ("Operation CHAOS", "Operation CHAOS"),
    "MONGOOSE": ("Operation Mongoose", "Operation Mongoose"),
    "ZAPATA": ("the Bay of Pigs invasion", "Bay of Pigs Invasion"),
    "BAY OF PIGS": ("the Bay of Pigs invasion", "Bay of Pigs Invasion"),
    "PBSUCCESS": ("the 1954 Guatemalan coup", "1954 Guatemalan coup d'état"),
    "TPAJAX": ("the 1953 Iranian coup", "1953 Iranian coup d'état"),
    "KUBARK": ("the KUBARK interrogation manual", "KUBARK Counterintelligence Interrogation"),
    "PHOENIX": ("the Phoenix Program", "Phoenix Program"),
    "VENONA": ("the Venona project", "Venona project"),
    "NORTHWOODS": ("Operation Northwoods", "Operation Northwoods"),
    "ABLE ARCHER": ("Able Archer 83", "Able Archer 83"),
    "MOCKINGBIRD": ("Operation Mockingbird", "Operation Mockingbird"),
    "PAPERCLIP": ("Operation Paperclip", "Operation Paperclip"),
    "BLUE BOOK": ("Project Blue Book", "Project Blue Book"),
    "PROJECT SIGN": ("Project Sign", "Project Sign"), "GRUDGE": ("Project Grudge", "Project Grudge"),
    "COINTELPRO": ("COINTELPRO", "COINTELPRO"),
    "AREA 51": ("Area 51", "Area 51"), "GROOM LAKE": ("Area 51", "Area 51"),
    "ROSWELL": ("the Roswell incident", "Roswell incident"),
    "FAMILY JEWELS": ("the CIA “Family Jewels”", "Family Jewels (Central Intelligence Agency)"),
    "CHURCH COMMITTEE": ("the Church Committee", "Church Committee"),
    "PENTAGON PAPERS": ("the Pentagon Papers", "Pentagon Papers"),
    "GULF OF TONKIN": ("the Gulf of Tonkin incident", "Gulf of Tonkin incident"),
    "CUBAN MISSILE CRISIS": ("the Cuban Missile Crisis", "Cuban Missile Crisis"),
    "MANHATTAN PROJECT": ("the Manhattan Project", "Manhattan Project"),
    "PRESIDENT'S DAILY BRIEF": ("the President's Daily Brief", "President's Daily Brief"),
}


def find_program(text):
    """The best-known program named in a search or document title, or None. Longest names first."""
    U = (text or "").upper()
    for term in sorted(PROGRAMS, key=len, reverse=True):
        if re.search(r"(?<![A-Z0-9])" + re.escape(term) + r"(?![A-Z0-9])", U):
            name, article = PROGRAMS[term]
            return {"term": term, "name": name, "article": article}
    return None


def wiki_summary(article):
    """{'title', 'extract', 'url', 'thumb'} from Wikipedia's summary service, or None if not found."""
    r = requests.get("https://en.wikipedia.org/api/rest_v1/page/summary/" +
                     urllib.parse.quote(article.replace(" ", "_"), safe=""), headers=_UA, timeout=15)
    if r.status_code != 200:
        return None
    d = r.json()
    if d.get("type") == "disambiguation" or not d.get("extract"):
        return None
    return {"title": d.get("title", article), "extract": d["extract"],
            "url": d.get("content_urls", {}).get("desktop", {}).get("page",
                   "https://en.wikipedia.org/wiki/" + urllib.parse.quote(article.replace(" ", "_"))),
            "thumb": (d.get("thumbnail") or {}).get("source")}
