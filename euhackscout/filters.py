from __future__ import annotations

import re
from datetime import date

from euhackscout.models import Format, Hackathon, fold

_IX = re.IGNORECASE | re.VERBOSE

HACKATHON_RE = re.compile(
    r"""
    \b(
        hackathons?
        | hackatons?
        | hackathoane
        | hackathoanele
        | hack[\s-]?days?
        | hack[\s-]?nights?
        | datathons?
        | codefests?
        | game[\s-]?jams?
        | buildathons?
        | makeathons?
        | \bjams?\b
        | BESTEM
        | HackITAll
        | Smarthack
        | PoliHack
        | Electron[\s-]?Hack
        | GitGood
        | Space[\s-]?Apps
        | Innovation[\s-]?Labs
        | EESTEC
        | CAD\s*&\s*CRAFT
        | 24[\s-]?Hours[\s-]?of[\s-]?Google
    )\b
    """,
    _IX,
)

BUCHAREST_RE = re.compile(
    r"""
    \b(
        bucure[sşș]ti
        | bucharest
        | bukarest
        | ilfov
        | otopeni
        | voluntari
        | pipera
        | popesti
        | popești
    )\b
    """,
    _IX,
)

EUROPE_RE = re.compile(
    r"""
    \b(
        europe|europa|emea|eea
        | romania|rom[aâ]nia
        | united[\s-]?kingdom|\buk\b|england|scotland|wales
        | ireland|germany|deutschland|france|netherlands|holland
        | belgium|luxembourg|switzerland|austria|spain|portugal
        | italy|poland|czech|slovakia|hungary|croatia|slovenia
        | denmark|sweden|norway|finland|iceland|estonia|latvia
        | lithuania|greece|cyprus|malta|bulgaria|serbia
        | bosnia|montenegro|albania|moldova|ukraine
        | london|londra|amsterdam|berlin|paris|dublin|madrid
        | barcelona|lisbon|lisboa|zurich|zürich|geneva|vienna
        | wien|prague|praha|warsaw|warszawa|krakow|budapest
        | copenhagen|stockholm|oslo|helsinki|tallinn|riga
        | vilnius|athens|milan|milano|rome|roma|munich|münchen
        | frankfurt|hamburg|brussels|bruxelles|antwerp|rotterdam
        | cluj|iasi|iași|timisoara|timișoara|brasov|brașov
        | sibiu|oradea|craiova|constanta|constanța
        | bucharest|bucure[sşș]ti
    )\b
    | ,\s*(RO|DE|FR|IT|ES|NL|BE|AT|CH|PL|CZ|HU|SE|DK|NO|FI|IE|PT|GR|BG|HR|SK|SI|LT|LV|EE|LU|MT|CY|RS|MD|UA|GB|UK)\b
    """,
    _IX,
)

NON_EUROPE_RE = re.compile(
    r"""
    \b(
        united[\s-]?states
        | u\.?s\.?a\.?
        | chicago|nyc|new[\s-]?york|boston|san[\s-]?francisco
        | palo[\s-]?alto|seattle|austin|dallas|houston|miami
        | denver|atlanta|los[\s-]?angeles|san[\s-]?jose
        | california|texas|florida|canada|toronto|vancouver
        | montreal|india|indian|bangalore|bengaluru|mumbai
        | delhi|hyderabad|chennai|pune|noida|kerala
        | china|beijing|shanghai|shenzhen
        | japan|tokyo|osaka
        | singapore|hong[\s-]?kong
        | australia|sydney|melbourne
        | brazil|sao[\s-]?paulo
        | korea|seoul
        | nigeria|lagos
        | egypt|cairo
        | kenya|nairobi
        | mexico
        | pakistan|karachi
        | bangladesh
        | indonesia|jakarta
        | vietnam|hanoi
        | philippines|manila
        | taiwan|taipei
        | thailand|bangkok
        | malaysia
        | uae|dubai
        | israel|tel[\s-]?aviv
        | south[\s-]?africa
        | argentina|chile
        | new[\s-]?zealand
    )\b
    | ,\s*(NY|IL|CA|MA|TX|WA|FL|NJ|CT|CO|GA|PA|DC|ON|IN|CN|JP|KR|AU|BR|MX|NG|EG|KE|PK|BD|ID|VN|PH|TW|TH|MY|AE|IL|ZA|AR|CL|NZ)\b
    | \bUSA\b
    """,
    _IX,
)


def effective_deadline(hackathon: Hackathon) -> date | None:
    return hackathon.registration_deadline or hackathon.end_date or hackathon.start_date


def is_active(hackathon: Hackathon, today: date | None = None) -> bool:
    today = today or date.today()
    deadline = effective_deadline(hackathon)
    if deadline is None:
        return True
    return deadline >= today


def is_bucharest(loc: str) -> bool:
    blob = loc or ""
    return bool(BUCHAREST_RE.search(blob) or BUCHAREST_RE.search(fold(blob)))


def is_europe(loc: str) -> bool:
    blob = loc or ""
    folded = fold(blob)
    if is_bucharest(blob):
        return True
    return bool(EUROPE_RE.search(blob) or EUROPE_RE.search(folded))


def is_online(fmt: Format) -> bool:
    return fmt is Format.ONLINE


def is_hackathon(name: str, extra: str = "") -> bool:
    blob = f"{name} {extra}"
    return bool(HACKATHON_RE.search(blob) or HACKATHON_RE.search(fold(blob)))


def is_stale_edition(name: str, today: date | None = None) -> bool:
    """Drop 'HackITAll 2024' retrospectives when the title year is already past."""
    today = today or date.today()
    years = [int(y) for y in re.findall(r"(?<!\d)(20\d{2})\b", name or "")]
    return bool(years) and max(years) < today.year


def keep_hackathon(
    hackathon: Hackathon,
    today: date | None = None,
    *,
    require_keyword: bool = False,
    assume_bucharest: bool = False,
) -> bool:
    if not is_active(hackathon, today):
        return False
    if is_stale_edition(hackathon.name, today):
        return False
    if require_keyword and not is_hackathon(hackathon.name, f"{hackathon.organizer} {hackathon.location}"):
        return False
    loc = hackathon.location
    if assume_bucharest and not loc.strip():
        loc = "Bucharest, Romania"
    if is_online(hackathon.format):
        return True
    if is_europe(loc):
        return True
    if NON_EUROPE_RE.search(loc) or NON_EUROPE_RE.search(fold(loc)):
        return False
    return False
