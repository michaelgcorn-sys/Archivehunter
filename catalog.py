"""
Curated content for the Explore and Ancient Intelligence tabs.

Every hand-picked item here was checked against its source in Oct 2026 (title, date and wording).
Anything that couldn't be confirmed was left out. Each Explore category also pulls featured
documents live from the CIA reading room mirror, so those titles are the CIA's own.
"""

import requests

CATALOG_VERSION = 58   # keep in step with APP_CODE_VERSION in app.py

from sources import HEADERS, _res

IA = "https://archive.org/details/cia-readingroom-document-"
IA_TXT = "https://archive.org/download/cia-readingroom-document-{id}/{id}_djvu.txt"
IA_PDF = "https://archive.org/download/cia-readingroom-document-{id}/{id}.pdf"


def _cia(doc_id, title, date, blurb):
    return _res("CIA", title, IA + doc_id, date=date, kind=f"CIA document {doc_id.upper()}",
                snippet=blurb, doc_url=IA_TXT.format(id=doc_id), file_url=IA_PDF.format(id=doc_id))


def _gwu(title, url, date, blurb, pdf=None):
    return _res("GWU Natl Security Archive", title, url, date=date, kind="National Security Archive",
                snippet=blurb, doc_url=pdf or url, file_url=pdf)


# Hand-picked documents, verified against the source
PICKS = {
    "northwoods": _gwu(
        "Operation Northwoods: Joint Chiefs memo, “Justification for US Military Intervention in Cuba”",
        "https://nsarchive.gwu.edu/CMC-60/joint-chiefs-pretexts-to-invade-Cuba-1962", "1962",
        "TOP SECRET SPECIAL HANDLING NOFORN, 13 March 1962. The Joint Chiefs proposed staged pretexts for "
        "invading Cuba, including a faked shoot-down of a civilian airliner.",
        pdf="https://nsarchive.gwu.edu/sites/default/files/2022-10/Joint-Chiefs-pretexts-to-invade-Cuba-March-1962_0.pdf"),
    "assassination_plots": _cia(
        "cia-rdp83-01042r000200090002-0", "Alleged Assassination Plots Involving Foreign Leaders", "1975",
        "CIA file dated 20 November 1975, the day the Senate’s Church Committee released its report of the same "
        "name on U.S. plots against foreign leaders."),
    "kugown": _cia(
        "0000915588", "KUGOWN: Black operation against José Manuel Fortuny Arana", "1954",
        "April 1954 CIA “black” operation against a Guatemalan communist leader, two months before the "
        "CIA-backed coup in Guatemala."),
    "able_archer": _gwu(
        "“The Soviet ‘War Scare’”: President's Foreign Intelligence Advisory Board report",
        "https://nsarchive.gwu.edu/document/33591-document-4-authoritative-presidents-foreign-intelligence-advisory-board-report",
        "1990", "Declassified in 2015. Concludes the Soviets were genuinely worried that NATO's 1983 "
        "Able Archer exercise could be cover for a real nuclear attack."),
    "chile": _gwu(
        "CIA Cover-Up on Chile", "https://nsarchive.gwu.edu/briefing-book/chile/2016-09-09/cia-cover-chile",
        "2016", "The National Security Archive on CIA records about the 1973 Chile coup that the agency "
        "still withholds, including what it told President Nixon."),
}

# Explore categories: (name, icon, live CIA-mirror query, main-search query, hand-picked ids)
CATEGORIES = [
    ("Presidential Daily Briefs", "📜", 'title:"president\'s daily brief"', "President's Daily Brief", []),
    ("Assassination Plots", "🎯", "assassination", "assassination plot", ["assassination_plots"]),
    ("Coups & Covert Action", "🕴", "covert action", "covert action coup", ["kugown", "chile"]),
    ("Cuba", "🇨🇺", "Cuba", "Cuba", ["northwoods"]),
    ("Secret Experiments", "🧪", "MKULTRA", "MKUltra", []),
    ("Psychic Spies", "🔮", "GRILL FLAME", "remote viewing", []),
    ("UFO Files", "🛸", "UFO", "UFO", []),
    ("Spy Satellites", "🛰", "CORONA satellite", "CORONA satellite", []),
    ("Secret Aircraft", "✈️", "OXCART", "OXCART U-2", []),
    ("Soviet Espionage", "☭", "KGB", "KGB espionage", []),
    ("Nuclear Close Calls", "☢️", "nuclear war", "nuclear war scare", ["able_archer"]),
    ("Vietnam", "🎖", "Vietnam", "Vietnam", []),
]


# One-line teasers for the deep-dive tiles
TEASERS = {
    "Presidential Daily Briefs": "What JFK, LBJ, Nixon and Ford read each morning",
    "Assassination Plots": "Plots against foreign leaders, in the government's own files",
    "Coups & Covert Action": "Secret operations to topple governments",
    "Cuba": "Operation Northwoods, Castro and the missile crisis",
    "Secret Experiments": "MKULTRA and the CIA's mind-control research",
    "Psychic Spies": "GRILL FLAME, STARGATE and remote viewing",
    "UFO Files": "Saucers and sightings in the CIA's files",
    "Spy Satellites": "CORONA and the first spy cameras in orbit",
    "Secret Aircraft": "OXCART, the U-2 and Area 51",
    "Soviet Espionage": "The KGB, defectors and double agents",
    "Nuclear Close Calls": "When the Cold War nearly went hot",
    "Vietnam": "Intelligence files from the war",
}


# Ancient Intelligence: verified items with translations quoted from the source
ANCIENT = [
    {
        "title": "The Harem Conspiracy: a plot to kill Pharaoh",
        "lang": "Ancient Egyptian, in hieratic script on papyrus",
        "where": "Egypt · reign of Ramesses III, about 1155 BC · papyrus court record",
        "what": "Trial record of the conspirators who plotted to murder Ramesses III. A queen, Tiye, worked "
                "with harem women and palace officials to put her son Pentaweret on the throne. Scans of the "
                "king's mummy in 2012 found his throat had been cut, so the plot may well have worked, but "
                "his chosen heir still became king and the plotters went on trial.",
        "quote": None,
        "source": "Judicial Papyrus of Turin, Cat. 1875 (Museo Egizio)",
        "url": "https://collezionepapiri.museoegizio.it/en-GB/document/391/",
        "met_id": None,
    },
    {
        "title": "The tomb-robbery investigation",
        "lang": "Ancient Egyptian, in hieratic script on papyrus",
        "where": "Thebes, Egypt · 20th Dynasty, about 1110 BC · papyrus",
        "what": "Official inquiry into the looting of royal tombs, in which two rival officials of Thebes "
                "traded accusations over who was protecting the robbers. A 3,000-year-old corruption probe.",
        "quote": None,
        "source": "The Abbott Papyrus, EA 10221,1 (British Museum)",
        "url": "https://www.britishmuseum.org/collection/object/Y_EA10221-1",
        "met_id": None,
    },
    {
        "title": "A Roman curse on a cloak thief",
        "lang": "Latin, scratched into lead",
        "where": "Bath, Roman Britain · AD 100s–300s · lead tablet thrown into the sacred spring",
        "what": "A victim of theft asks the goddess to punish whoever stole a hooded cloak. More than 100 of "
                "these curse tablets were found in the spring at Bath.",
        "quote": "To Minerva the goddess Sulis I have given the thief who has stolen my hooded cloak, whether "
                 "slave or free, whether man or woman. He is not to buy back this gift unless with his own blood.",
        "source": "Tab. Sulis 65 (Roman Inscriptions of Britain)",
        "url": "https://romaninscriptionsofbritain.org/inscriptions/TabSulis65",
        "met_id": None,
    },
    {
        "title": "A Coup d’État in Urartu",
        "lang": "Neo-Assyrian Akkadian, in cuneiform on clay",
        "where": "Assyria · reign of Sargon II, 8th century BC · clay tablet",
        "what": "An intelligence report to the Assyrian king on a palace coup in the rival kingdom of Urartu.",
        "quote": "His magnates surrounded him… and killed him. The right-hand commander-in-chief, of the family "
                 "of Sarduri, […] but has not yet entered Ṭurušpâ.",
        "source": "State Archives of Assyria, SAA 05 093 (ORACC)",
        "url": "https://oracc.museum.upenn.edu/saao/saa05/P313779/html",
        "met_id": None,
    },
    {
        "title": "A Roman officer sizes up the Britons",
        "lang": "Latin, handwritten in ink on wood",
        "where": "Vindolanda fort, Roman Britain · about AD 92 · ink on a wooden tablet",
        "what": "A Roman military memo on how the local Britons fight, using the mocking word “Brittunculi,” "
                "“little Brits.”",
        "quote": "The Britons are unprotected by armor. There are very many cavalry. The cavalry do not use swords "
                 "nor do the Brittunculi mount in order to throw javelins.",
        "source": "Vindolanda tablet 164 (Roman Inscriptions of Britain)",
        "url": "https://romaninscriptionsofbritain.org/inscriptions/TabVindol164",
        "met_id": None,
    },
    {
        "title": "Gezer begs Pharaoh for help",
        "lang": "Akkadian (the diplomatic language of the day), in cuneiform on clay",
        "where": "Canaan · Amarna period, 14th century BC · clay tablet",
        "what": "Yapahu, ruler of Gezer, asks the Egyptian king for military help against raiders called the "
                "Habiru.",
        "quote": "Since the [‘Apiru] are stronger than we, may the king, my lord, (g)ive me his help.",
        "source": "Amarna letter EA 299, British Museum",
        "url": "https://www.britishmuseum.org/collection/object/W_1888-1013-45",
        "met_id": None,
    },
    {
        "title": "Assyria writes to Egypt",
        "lang": "Akkadian, in cuneiform on clay",
        "where": "Assyria to Egypt · about 1347–1330 BC · clay tablet",
        "what": "Royal letter from Ashur-uballit, King of Assyria, to the King of Egypt, written in the "
                "diplomatic language of the age.",
        "quote": None,
        "source": "Amarna letter, Metropolitan Museum of Art",
        "url": "https://www.metmuseum.org/art/collection/search/544695",
        "met_id": 544695,
    },
    {
        "title": "A report from Tyre",
        "lang": "Akkadian, in cuneiform on clay",
        "where": "Tyre to Egypt · about 1347–1330 BC · unfired clay tablet",
        "what": "Royal letter from Abi-milku, ruler of the port city of Tyre, to the King of Egypt.",
        "quote": None,
        "source": "Amarna letter, Metropolitan Museum of Art",
        "url": "https://www.metmuseum.org/art/collection/search/544696",
        "met_id": 544696,
    },
]


def met_image(object_id):
    """Public-domain photo of a Metropolitan Museum object, via the Met's free official API."""
    d = requests.get(f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{object_id}",
                     headers=HEADERS, timeout=15).json()
    return d.get("primaryImageSmall") or d.get("primaryImage") or None


def met_gallery(q="Amarna letter", limit=8):
    """More ancient tablets from the Met's public-domain collection (live)."""
    ids = requests.get("https://collectionapi.metmuseum.org/public/collection/v1/search",
                       params={"q": q, "hasImages": "true"}, headers=HEADERS, timeout=15).json().get("objectIDs") or []
    out = []
    for oid in ids[:limit * 2]:
        try:
            d = requests.get(f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{oid}",
                             headers=HEADERS, timeout=15).json()
        except Exception:
            continue
        img = d.get("primaryImageSmall")
        if not img or not d.get("isPublicDomain"):
            continue
        out.append({"title": d.get("title", ""), "date": d.get("objectDate", ""), "img": img,
                    "url": d.get("objectURL", f"https://www.metmuseum.org/art/collection/search/{oid}")})
        if len(out) >= limit:
            break
    return out


# Corporate Secrets: internal company records made public through lawsuits, leaks and investigations.
# Kept separate from the government search. Counts are given only where the host's own page states them.
CORPORATE = [
    {"title": "Big Tobacco", "icon": "🚬", "search": "nicotine addiction",
     "what": "The tobacco companies' own research, marketing plans and memos, forced into the open by "
             "lawsuits in the 1990s. The biggest corporate-secrets archive there is.",
     "source": "Truth Tobacco Industry Documents (UCSF)",
     "url": "https://www.industrydocuments.ucsf.edu/tobacco/"},
    {"title": "The Opioid Files", "icon": "💊", "search": "McKinsey OxyContin",
     "what": "Records from the opioid lawsuits, including McKinsey's advice to opioid makers on how to "
             "sell more pills.",
     "source": "Opioid Industry Documents Archive (UCSF)",
     "url": "https://www.industrydocuments.ucsf.edu/opioids/"},
    {"title": "Coca-Cola and the Sugar Science", "icon": "🥤", "search": "Global Energy Balance Network",
     "what": "Internal Coca-Cola emails about shaping public-health policy, and records on its funding of "
             "a research group that pushed exercise over cutting sugar.",
     "source": "Food Industry Documents (UCSF)",
     "url": "https://www.industrydocuments.ucsf.edu/food/collections/coca-cola-emails/"},
    {"title": "Forever Chemicals", "icon": "🧪", "search": "DuPont C8",
     "what": "DuPont records on the toxicity of C8 (PFOA), the litigation, and how the company handled "
             "the message, plus a large European investigation of PFAS lobbying.",
     "source": "Chemical Industry Documents (UCSF)",
     "url": "https://www.industrydocuments.ucsf.edu/chemical/collections/pfas-collection/"},
    {"title": "Big Oil and Climate", "icon": "🛢", "search": "Exxon climate",
     "what": "Oil-industry research, policy strategy and climate messaging, including a Shell and "
             "Exxon set.",
     "source": "Fossil Fuel Industry Documents (UCSF)",
     "url": "https://www.industrydocuments.ucsf.edu/fossilfuel/"},
    {"title": "The Poison Papers", "icon": "☠️", "search": "dioxin",
     "what": "About 20,000 documents (250,000+ pages) from chemical makers and regulators, including Dow, "
             "Monsanto and DuPont, on Agent Orange, dioxins, PCBs and pesticides. Pried loose through "
             "FOIA requests and lawsuits.",
     "source": "Bioscience Resource Project",
     "url": "https://bioscienceresource.org/document-leaks/the-poison-papers/"},
    {"title": "The Enron Emails", "icon": "📧", "search": None,
     "what": "About half a million emails from roughly 150 Enron employees, mostly senior management. "
             "Made public by federal energy regulators during their investigation.",
     "source": "Enron Email Dataset (Carnegie Mellon)",
     "url": "https://www.cs.cmu.edu/~enron/"},
    {"title": "Facebook and Cambridge Analytica", "icon": "👍", "search": None,
     "what": "Confidential Facebook documents seized and published by the British Parliament, alongside "
             "Cambridge Analytica evidence from Alexander Nix, Christopher Wylie and Brittany Kaiser.",
     "source": "UK Parliament, Disinformation and ‘fake news’ inquiry",
     "url": "https://committees.parliament.uk/work/6330/disinformation-and-fake-news/publications/14/older-evidence/"},
    {"title": "Microsoft on Trial", "icon": "🖥", "search": None,
     "what": "The government's original exhibits from the browser-war antitrust trial: Microsoft's "
             "internal emails and memos.",
     "source": "U.S. Justice Department, Antitrust Division",
     "url": "https://www.justice.gov/atr/us-v-microsoft-corporation-browser-and-middleware-trial-exhibits"},
]
