from __future__ import annotations

import re
from typing import List, Optional, Tuple

MONTHS = {
    "i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10, "xi": 11, "xii": 12,
    "januar": 1, "januara": 1, "jan": 1,
    "februar": 2, "februara": 2, "feb": 2,
    "mart": 3, "marta": 3, "mar": 3,
    "april": 4, "aprila": 4, "apr": 4,
    "maj": 5, "maja": 5,
    "jun": 6, "juna": 6, "juni": 6,
    "jul": 7, "jula": 7, "juli": 7,
    "avgust": 8, "avgusta": 8, "august": 8,
    "septembar": 9, "septembra": 9, "sep": 9,
    "oktobar": 10, "oktobra": 10, "okt": 10,
    "novembar": 11, "novembra": 11, "nov": 11,
    "decembar": 12, "decembra": 12, "dec": 12,
    "siječanj": 1, "siječnja": 1, "sijecanj": 1, "sijecnja": 1,
    "veljača": 2, "veljače": 2, "veljaca": 2, "veljace": 2,
    "ožujak": 3, "ožujka": 3, "ozujak": 3, "ozujka": 3,
    "travanj": 4, "travnja": 4,
    "svibanj": 5, "svibnja": 5,
    "lipanj": 6, "lipnja": 6,
    "srpanj": 7, "srpnja": 7,
    "kolovoz": 8, "kolovoza": 8,
    "rujan": 9, "rujna": 9,
    "listopad": 10, "listopada": 10,
    "studeni": 11, "studenog": 11, "studenoga": 11,
    "prosinac": 12, "prosinca": 12,
}

ROMAN_MONTHS = frozenset(
    {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii"}
)

# Longest alternatives come first so, for example, ``septembra`` is preferred
# to the abbreviation ``sep``. Word boundaries prevent either one from being
# accepted as only the prefix of an unknown word.
TEXT_MONTH_PATTERN = "|".join(
    re.escape(month)
    for month in sorted(MONTHS.keys() - ROMAN_MONTHS, key=len, reverse=True)
)

DATE_MENTION_PATTERNS = [
    # 2. II 1927 / 2. II. 1927 / 11. 1. 1914
    re.compile(
        r"\b\d{1,2}\s*\.\s*(?:[IVXLCDM]+|\d{1,2})(?:\s*\.\s*|\s+)\d{2,4}\b",
        re.I,
    ),
    # 2 februara 1927 / 20. aprila 1927 / 2. feb. 1927
    re.compile(
        rf"\b\d{{1,2}}\s*\.?\s+(?:{TEXT_MONTH_PATTERN})\.?\s+\d{{2,4}}\b",
        re.I,
    ),
    # Standalone four-digit years. Nested years are removed by find_date_spans.
    re.compile(r"\b\d{4}\b"),
]

PLACE_DATE_PATTERNS = [
    # Beograd 24. II. 26 / Berlin 11. aprila 1939 g.
    re.compile(r"(?P<place>[A-ZČĆŽŠĐA-Z][\wČĆŽŠĐčćžšđ\-. ]{1,40}?)[, ]+\s*(?P<day>\d{1,2})\s*\.\s*(?P<month>[IVXLCDM]+|[A-Za-zČĆŽŠĐčćžšđ]+)\.?\s*(?P<year>\d{2,4})", re.I),
    # Marseille 2 februara 1927
    re.compile(r"(?P<place>[A-ZČĆŽŠĐA-Z][\wČĆŽŠĐčćžšđ\-. ]{1,40}?)[, ]+\s*(?P<day>\d{1,2})\s+(?P<month>[A-Za-zČĆŽŠĐčćžšđ]+)\s+(?P<year>\d{2,4})", re.I),
    # (Zagreb, 11. 1. 1914)
    re.compile(r"\(?(?P<place>[A-ZČĆŽŠĐA-Z][\wČĆŽŠĐčćžšđ\-. ]{1,40}?)[, ]+\s*(?P<day>\d{1,2})\s*\.\s*(?P<month>\d{1,2})\s*\.\s*(?P<year>\d{2,4})", re.I),
]

DATE_ONLY_PATTERNS = [
    re.compile(r"(?P<day>\d{1,2})\s*\.\s*(?P<month>[IVXLCDM]+|\d{1,2}|[A-Za-zČĆŽŠĐčćžšđ]+)\.?\s*(?P<year>\d{2,4})", re.I),
]


def find_date_spans(text: str) -> List[Tuple[int, int]]:
    """Return non-overlapping date spans, preferring complete expressions.

    The patterns deliberately include standalone years as a fallback. When a
    year is part of a complete expression such as ``20 aprila 1927``, only the
    complete expression is returned.
    """
    candidates = {
        (match.start(), match.end())
        for pattern in DATE_MENTION_PATTERNS
        for match in pattern.finditer(text)
    }

    complete_spans = []
    for start, end in candidates:
        is_contained = any(
            other_start <= start
            and end <= other_end
            and (other_start, other_end) != (start, end)
            for other_start, other_end in candidates
        )
        if not is_contained:
            complete_spans.append((start, end))

    return sorted(complete_spans)


def normalize_year(y: str) -> int:
    year = int(y)
    if year < 100:
        # Andrić letters in the selected book are early 20th century.
        return 1900 + year
    return year


def normalize_month(m: str) -> Optional[int]:
    m = m.strip(" .,").lower()
    if m.isdigit():
        n = int(m)
        return n if 1 <= n <= 12 else None
    return MONTHS.get(m)


def format_date(year: int, month: int, day: int) -> str:
    return f"{year:04d}-{month:02d}-{day:02d}"


def extract_place_and_date(text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Return (place, ISO date, matched_header)."""
    head = "\n".join(text.splitlines()[:12])
    for pat in PLACE_DATE_PATTERNS:
        m = pat.search(head)
        if m:
            month = normalize_month(m.group("month"))
            if month:
                year = normalize_year(m.group("year"))
                day = int(m.group("day"))
                place = m.group("place").strip(" ,.;:()[]")
                return place, format_date(year, month, day), m.group(0)

    for pat in DATE_ONLY_PATTERNS:
        m = pat.search(head)
        if m:
            month = normalize_month(m.group("month"))
            if month:
                year = normalize_year(m.group("year"))
                day = int(m.group("day"))
                return None, format_date(year, month, day), m.group(0)
    return None, None, None
