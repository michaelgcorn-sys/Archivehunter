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

MODULE_VERSION = 61   # keep in step with APP_CODE_VERSION in app.py

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


# What was happening in a place in a given year: used for "deep dive" searches like "Czechoslovakia 1968".
# (place names as they appear in briefs, first year, last year, display name, Wikipedia article)
EVENTS = [
    ("Czechoslovakia", 1968, 1969, "the Prague Spring and the Soviet invasion", "Warsaw Pact invasion of Czechoslovakia"),
    ("Nigeria", 1967, 1970, "the Nigerian Civil War (Biafra)", "Nigerian Civil War"),
    ("Vietnam", 1961, 1975, "the Vietnam War", "Vietnam War"),
    ("North Vietnam", 1961, 1975, "the Vietnam War", "Vietnam War"),
    ("South Vietnam", 1961, 1975, "the Vietnam War", "Vietnam War"),
    ("Laos", 1961, 1975, "the Laotian Civil War", "Laotian Civil War"),
    ("Cambodia", 1970, 1975, "the Cambodian Civil War", "Cambodian Civil War"),
    ("Cuba", 1962, 1962, "the Cuban Missile Crisis", "Cuban Missile Crisis"),
    ("Dominican Republic", 1965, 1966, "the Dominican Civil War and U.S. intervention", "Dominican Civil War"),
    ("Indonesia", 1965, 1966, "the 1965 coup attempt and mass killings", "Indonesian mass killings of 1965–66"),
    ("Israel", 1967, 1967, "the Six-Day War", "Six-Day War"), ("Egypt", 1967, 1967, "the Six-Day War", "Six-Day War"),
    ("Syria", 1967, 1967, "the Six-Day War", "Six-Day War"), ("Jordan", 1967, 1967, "the Six-Day War", "Six-Day War"),
    ("Israel", 1973, 1973, "the Yom Kippur War", "Yom Kippur War"), ("Egypt", 1973, 1973, "the Yom Kippur War", "Yom Kippur War"),
    ("Syria", 1973, 1973, "the Yom Kippur War", "Yom Kippur War"), ("Middle East", 1973, 1973, "the Yom Kippur War", "Yom Kippur War"),
    ("Middle East", 1967, 1967, "the Six-Day War", "Six-Day War"),
    ("Jordan", 1970, 1971, "Black September", "Black September"),
    ("Chile", 1970, 1973, "Allende's presidency and the 1973 coup", "1973 Chilean coup d'état"),
    ("Portugal", 1974, 1975, "the Carnation Revolution", "Carnation Revolution"),
    ("Cyprus", 1974, 1974, "the Turkish invasion of Cyprus", "Turkish invasion of Cyprus"),
    ("Greece", 1967, 1974, "the Greek military junta", "Greek junta"),
    ("India", 1971, 1971, "the Indo-Pakistani War of 1971", "Indo-Pakistani war of 1971"),
    ("Pakistan", 1971, 1971, "the Indo-Pakistani War of 1971", "Indo-Pakistani war of 1971"),
    ("Pakistan", 1965, 1965, "the Indo-Pakistani War of 1965", "Indo-Pakistani war of 1965"),
    ("India", 1965, 1965, "the Indo-Pakistani War of 1965", "Indo-Pakistani war of 1965"),
    ("China", 1966, 1976, "the Cultural Revolution", "Cultural Revolution"),
    ("China", 1969, 1969, "the Sino-Soviet border clashes", "Sino-Soviet border conflict"),
    ("Soviet Union", 1968, 1968, "the Soviet invasion of Czechoslovakia", "Warsaw Pact invasion of Czechoslovakia"),
    ("USSR", 1968, 1968, "the Soviet invasion of Czechoslovakia", "Warsaw Pact invasion of Czechoslovakia"),
    ("Soviet Union", 1972, 1972, "détente and the SALT I treaty", "Strategic Arms Limitation Talks"),
    ("USSR", 1972, 1972, "détente and the SALT I treaty", "Strategic Arms Limitation Talks"),
    ("Congo", 1960, 1965, "the Congo Crisis", "Congo Crisis"), ("Zaire", 1960, 1965, "the Congo Crisis", "Congo Crisis"),
    ("Rhodesia", 1965, 1977, "Rhodesia's break from Britain and the Bush War", "Rhodesian Bush War"),
    ("Angola", 1975, 1976, "the Angolan Civil War", "Angolan Civil War"),
    ("Panama", 1964, 1964, "the 1964 Flag Riots", "Martyrs' Day (Panama)"),
    ("Berlin", 1961, 1961, "the Berlin Crisis and the Wall", "Berlin Crisis of 1961"),
    ("East Germany", 1961, 1961, "the Berlin Crisis and the Wall", "Berlin Crisis of 1961"),
    ("Northern Ireland", 1968, 1977, "the Troubles", "The Troubles"),
    ("United Kingdom", 1968, 1977, "the Troubles in Northern Ireland", "The Troubles"),
    ("Ethiopia", 1974, 1975, "the overthrow of Haile Selassie", "Ethiopian Revolution"),
    ("Iraq", 1968, 1968, "the Ba'athist coup", "17 July Revolution"),
    ("Libya", 1969, 1969, "Qaddafi's coup", "1969 Libyan coup d'état"),
    ("Bangladesh", 1971, 1971, "the Bangladesh Liberation War", "Bangladesh Liberation War"),
]


def find_event(text):
    """'Czechoslovakia 1968' -> {'term','name','article'} for what was happening there then, or None."""
    m = re.search(r"\b(19[4-9]\d)\b", text or "")
    if not m:
        return None
    year = int(m.group(1))
    low = (text or "").lower()
    for place, y0, y1, name, article in EVENTS:
        if y0 <= year <= y1 and re.search(r"\b" + re.escape(place.lower()) + r"\b", low):
            return {"term": f"{place} {year}", "name": name, "article": article}
    return None
