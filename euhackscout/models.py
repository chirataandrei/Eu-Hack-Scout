from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any
import hashlib
import re
import unicodedata
from urllib.parse import urlparse


class Format(str, Enum):
    IN_PERSON = "in_person"
    HYBRID = "hybrid"
    ONLINE = "online"


_MONTHS = {
    "jan": 1, "january": 1, "ian": 1, "ianuarie": 1,
    "feb": 2, "february": 2, "februarie": 2,
    "mar": 3, "march": 3, "martie": 3,
    "apr": 4, "april": 4, "aprilie": 4,
    "may": 5, "mai": 5,
    "jun": 6, "june": 6, "iun": 6, "iunie": 6,
    "jul": 7, "july": 7, "iul": 7, "iulie": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9, "septembrie": 9,
    "oct": 10, "october": 10, "octombrie": 10,
    "nov": 11, "november": 11, "noiembrie": 11,
    "dec": 12, "december": 12, "decembrie": 12,
}

_RANGE_RE = re.compile(
    r"""
    (?P<d1>\d{1,2})
    (?:\s*[-–—]\s*(?P<d2>\d{1,2}))?
    \s+
    (?P<m>[A-Za-zăâîșț]+)
    (?:\s+(?P<y>\d{4}))?
    """,
    re.VERBOSE | re.IGNORECASE,
)
_MDY_RANGE_RE = re.compile(
    r"""
    (?P<m1>[A-Za-z]{3,})
    \s+(?P<d1>\d{1,2})(?!\d)
    (?:\s*[-–—]\s*(?:(?P<m2>[A-Za-z]{3,})\s+)?(?P<d2>\d{1,2})(?!\d))?
    (?:,?\s*(?P<y>\d{4}))?
    """,
    re.VERBOSE | re.IGNORECASE,
)
_ISO_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_DMY_RE = re.compile(r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b")
_YEAR_RE = re.compile(r"\b(20\d{2})\b")


def _plausible_year(value: int) -> bool:
    return 2020 <= value <= 2035


def _year_near(text: str, start: int, end: int, explicit: str | None = None) -> int:
    """Prefer a year written next to the date, not a random 20xx later in the HTML."""
    if explicit:
        try:
            year = int(explicit)
            if _plausible_year(year):
                return year
        except ValueError:
            pass
    before = text[max(0, start - 60) : start]
    after = text[end : min(len(text), end + 24)]
    before_years = [int(y) for y in _YEAR_RE.findall(before) if _plausible_year(int(y))]
    if before_years:
        return before_years[-1]
    after_years = [int(y) for y in _YEAR_RE.findall(after) if _plausible_year(int(y))]
    if after_years:
        return after_years[0]
    return date.today().year


def fold(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch)).lower()


def norm_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    host = (parsed.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = (parsed.path or "").rstrip("/")
    return f"{host}{path}"


def parse_date(value: Any) -> date | None:
    """Tolerate ISO, epoch ms/s, and human ranges like 'Jul 31 - Oct 01, 2026'."""
    if value is None or value is False:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e12:
            ts /= 1000.0
        if ts > 1e9:
            try:
                return datetime.utcfromtimestamp(ts).date()
            except (OSError, OverflowError, ValueError):
                return None
        return None
    text = str(value).strip()
    if not text:
        return None
    iso = _ISO_RE.search(text)
    if iso:
        try:
            return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    dmy = _DMY_RE.search(text)
    if dmy:
        try:
            return date(int(dmy.group(3)), int(dmy.group(2)), int(dmy.group(1)))
        except ValueError:
            pass
    matches = list(_RANGE_RE.finditer(text))
    if matches:
        last = matches[-1]
        month = _MONTHS.get(fold(last.group("m")))
        year = _year_near(text, last.start(), last.end(), last.group("y"))
        if month:
            try:
                return date(year, month, int(last.group("d1") if last.group("d2") is None else last.group("d2")))
            except ValueError:
                return None
    mdy = _MDY_RANGE_RE.search(text)
    if mdy and _MONTHS.get(fold(mdy.group("m1"))):
        start, end = parse_date_range(text)
        return end or start
    return None


def parse_date_range(value: Any) -> tuple[date | None, date | None]:
    """Parse 'Jul 31 - Oct 01, 2026' or '21-22 martie 2026' into (start, end)."""
    if value is None:
        return None, None
    text = str(value).strip()
    if not text:
        return None, None
    matches = list(_RANGE_RE.finditer(text))
    if matches and _MONTHS.get(fold(matches[0].group("m"))):
        first, last = matches[0], matches[-1]
        year = _year_near(text, first.start(), last.end(), last.group("y") or first.group("y"))
        m1 = _MONTHS.get(fold(first.group("m")))
        m2 = _MONTHS.get(fold(last.group("m")))
        start = None
        end = None
        if m1:
            try:
                start = date(year, m1, int(first.group("d1")))
            except ValueError:
                start = None
        if m2:
            day = int(last.group("d2") or last.group("d1"))
            try:
                end = date(year, m2, day)
            except ValueError:
                end = None
        if start and not end and first.group("d2"):
            try:
                end = date(year, m1, int(first.group("d2")))
            except ValueError:
                end = None
        if start or end:
            return start, end or start
    mdy = _MDY_RANGE_RE.search(text)
    if mdy and _MONTHS.get(fold(mdy.group("m1"))):
        m1 = _MONTHS.get(fold(mdy.group("m1")))
        m2 = _MONTHS.get(fold(mdy.group("m2") or mdy.group("m1")))
        y = _year_near(text, mdy.start(), mdy.end(), mdy.group("y"))
        start = end = None
        try:
            start = date(y, m1, int(mdy.group("d1")))
        except (TypeError, ValueError):
            start = None
        if mdy.group("d2"):
            try:
                end = date(y, m2, int(mdy.group("d2")))
            except (TypeError, ValueError):
                end = None
        return start, end or start
    d = parse_date(text)
    return d, d


def _uid_for(url: str, name: str) -> str:
    blob = f"{norm_url(url)}|{fold(name)}"
    return "hk:" + hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class Hackathon:
    name: str
    organizer: str
    url: str
    source: str
    location: str = ""
    format: Format = Format.ONLINE
    start_date: date | None = None
    end_date: date | None = None
    registration_deadline: date | None = None
    tags: tuple[str, ...] = ()

    @property
    def uid(self) -> str:
        return _uid_for(self.url, self.name)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["uid"] = self.uid
        payload["format"] = self.format.value
        for key in ("start_date", "end_date", "registration_deadline"):
            value = payload[key]
            payload[key] = value.isoformat() if isinstance(value, date) else None
        payload["tags"] = list(self.tags)
        return payload
