"""Places named in documents -> countries, for the 'Where these files point' map."""

import re

MODULE_VERSION = 69   # keep in step with APP_CODE_VERSION in app.py

# name as it appears in documents -> (ISO-3 country code, display name). Cold War names map to today's country.
PLACE_ISO = {
    "Soviet Union": ("RUS", "USSR / Russia"), "USSR": ("RUS", "USSR / Russia"), "Russia": ("RUS", "USSR / Russia"),
    "Moscow": ("RUS", "USSR / Russia"), "Kremlin": ("RUS", "USSR / Russia"), "Leningrad": ("RUS", "USSR / Russia"),
    "China": ("CHN", "China"), "Peking": ("CHN", "China"), "Beijing": ("CHN", "China"),
    "Cuba": ("CUB", "Cuba"), "Havana": ("CUB", "Cuba"), "Guantanamo": ("CUB", "Cuba"),
    "Vietnam": ("VNM", "Vietnam"), "North Vietnam": ("VNM", "Vietnam"), "South Vietnam": ("VNM", "Vietnam"),
    "Saigon": ("VNM", "Vietnam"), "Hanoi": ("VNM", "Vietnam"),
    "Laos": ("LAO", "Laos"), "Cambodia": ("KHM", "Cambodia"), "Thailand": ("THA", "Thailand"), "Burma": ("MMR", "Burma"),
    "North Korea": ("PRK", "North Korea"), "Pyongyang": ("PRK", "North Korea"), "South Korea": ("KOR", "South Korea"),
    "Korea": ("KOR", "Korea"), "Japan": ("JPN", "Japan"), "Tokyo": ("JPN", "Japan"), "Taiwan": ("TWN", "Taiwan"),
    "Philippines": ("PHL", "Philippines"), "Indonesia": ("IDN", "Indonesia"), "India": ("IND", "India"),
    "Pakistan": ("PAK", "Pakistan"), "Afghanistan": ("AFG", "Afghanistan"), "Kabul": ("AFG", "Afghanistan"),
    "Iran": ("IRN", "Iran"), "Tehran": ("IRN", "Iran"), "Iraq": ("IRQ", "Iraq"), "Baghdad": ("IRQ", "Iraq"),
    "Syria": ("SYR", "Syria"), "Lebanon": ("LBN", "Lebanon"), "Beirut": ("LBN", "Lebanon"),
    "Israel": ("ISR", "Israel"), "Jordan": ("JOR", "Jordan"), "Egypt": ("EGY", "Egypt"), "Cairo": ("EGY", "Egypt"),
    "Saudi Arabia": ("SAU", "Saudi Arabia"), "Yemen": ("YEM", "Yemen"), "Libya": ("LBY", "Libya"),
    "Algeria": ("DZA", "Algeria"), "Morocco": ("MAR", "Morocco"), "Ethiopia": ("ETH", "Ethiopia"),
    "Congo": ("COD", "Congo"), "Zaire": ("COD", "Congo"), "Angola": ("AGO", "Angola"), "Rhodesia": ("ZWE", "Rhodesia"),
    "South Africa": ("ZAF", "South Africa"), "Nigeria": ("NGA", "Nigeria"),
    "Mexico": ("MEX", "Mexico"), "Mexico City": ("MEX", "Mexico"), "Guatemala": ("GTM", "Guatemala"),
    "Nicaragua": ("NIC", "Nicaragua"), "Panama": ("PAN", "Panama"), "El Salvador": ("SLV", "El Salvador"),
    "Dominican Republic": ("DOM", "Dominican Republic"), "Haiti": ("HTI", "Haiti"), "Chile": ("CHL", "Chile"),
    "Santiago": ("CHL", "Chile"), "Peru": ("PER", "Peru"), "Bolivia": ("BOL", "Bolivia"), "Brazil": ("BRA", "Brazil"),
    "Argentina": ("ARG", "Argentina"), "Venezuela": ("VEN", "Venezuela"), "Colombia": ("COL", "Colombia"),
    "Canada": ("CAN", "Canada"), "United Kingdom": ("GBR", "United Kingdom"), "Britain": ("GBR", "United Kingdom"),
    "London": ("GBR", "United Kingdom"), "Northern Ireland": ("GBR", "United Kingdom"), "Ireland": ("IRL", "Ireland"),
    "France": ("FRA", "France"), "Paris": ("FRA", "France"), "Germany": ("DEU", "Germany"),
    "West Germany": ("DEU", "Germany"), "East Germany": ("DEU", "Germany"), "Berlin": ("DEU", "Germany"),
    "Italy": ("ITA", "Italy"), "Rome": ("ITA", "Italy"), "Spain": ("ESP", "Spain"), "Portugal": ("PRT", "Portugal"),
    "Greece": ("GRC", "Greece"), "Turkey": ("TUR", "Turkey"), "Cyprus": ("CYP", "Cyprus"),
    "Yugoslavia": ("SRB", "Yugoslavia"), "Albania": ("ALB", "Albania"), "Romania": ("ROU", "Romania"),
    "Bulgaria": ("BGR", "Bulgaria"), "Hungary": ("HUN", "Hungary"), "Budapest": ("HUN", "Hungary"),
    "Czechoslovakia": ("CZE", "Czechoslovakia"), "Prague": ("CZE", "Czechoslovakia"), "Poland": ("POL", "Poland"),
    "Warsaw": ("POL", "Poland"), "Austria": ("AUT", "Austria"), "Vienna": ("AUT", "Austria"),
    "Switzerland": ("CHE", "Switzerland"), "Geneva": ("CHE", "Switzerland"), "Sweden": ("SWE", "Sweden"),
    "Norway": ("NOR", "Norway"), "Finland": ("FIN", "Finland"), "Netherlands": ("NLD", "Netherlands"),
    "Belgium": ("BEL", "Belgium"), "Denmark": ("DNK", "Denmark"), "Mongolia": ("MNG", "Mongolia"),
    "Tibet": ("CHN", "China"), "Australia": ("AUS", "Australia"), "Nevada": ("USA", "United States"),
    "Area 51": ("USA", "United States"), "Roswell": ("USA", "United States"), "Dallas": ("USA", "United States"),
    "New Mexico": ("USA", "United States"),
}
_PAT = {name: re.compile(r"\b" + re.escape(name) + r"\b", re.I) for name in PLACE_ISO}


def countries_in(text):
    """{ISO-3: display name} for every country a piece of text names (once each)."""
    out = {}
    for name, rx in _PAT.items():
        if rx.search(text or ""):
            iso, disp = PLACE_ISO[name]
            out[iso] = disp
    return out


def decade_of(date):
    m = re.match(r"(1[89]\d|20[0-2])\d", str(date or ""))
    return f"{m.group(1)}0s" if m else None
