from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Dict, Iterable, List

from .pagexml import PageLine
from .utils import normalize_text, dehyphenate_linebreaks


@dataclass
class LetterRecord:
    letter_id: str
    source_page_files: str
    source_pages: str
    raw_header: str
    text: str


# Place names and OCR/script variants that occur in the selected corpus.
PLACE_PATTERN = (
    r"Beograd|Zagreb|Sarajevo|Marseille|Marselj|Mapcej|Mарсеј|Марсеј|"
    r"Geneve|Ženeva|Zeneva|Berlin|"
    r"Višegrad|Visegrad|Atina|Dubrovnik|Bukurest|"
    r"Београд|Загреб|Сарајево|Марсеј|Женева|Берлин|Вишеград|Атина|Дубровник|Букурешт"
)


# Header examples:
# Сарајево. II. II 1925.
# Београд, 1. IV 1925.
# Beograd 2. IV. 25.
# Marseille 2 februara 1927
# Ženeva, 14 oktobra 1930 g.
HEADER_RE = re.compile(
    rf"^\s*({PLACE_PATTERN})\s*[,.\-:]?\s+.*("
    r"\d{1,2}\s*[., ]\s*[IVXLCDM]{1,5}\s*[., ]*\s*\d{2,4}"
    r"|[IVXLCDM]{1,5}\s*[., ]\s*[IVXLCDM]{1,5}\s*[., ]*\s*\d{2,4}"
    r"|\d{1,2}\s+(januara|februara|marta|aprila|maja|juna|jula|avgusta|septembra|oktobra|novembra|decembra)\s+\d{4}"
    r")",
    re.IGNORECASE,
)


SALUTATION_RE = re.compile(
    r"(?i)\b(Draga|Dragi|Poštovana|Postovana|Poštovani|Postovani|gospođice|gospodice)\b"
)


SIGNATURE_RE = re.compile(
    r"(?i)\b(Vaš|Vas|Tvoj|Tvoja|Ivo\s+Andrić|Ivo\s+Andric|I\.\s*Andrić|I\.\s*Andric)\b"
)


ADDRESS_RE = re.compile(
    r"(?i)^\s*\[?\s*(Адреса|Adresa)\s*:?\]?\s*$"
)

def _text_of(lines: List[PageLine]) -> str:
    """
    Join PAGE XML lines into one letter text and repair words broken
    across line breaks, e.g. Polj-\\nsku -> Poljsku.
    """
    raw = "\n".join(x.text for x in lines if x.text.strip())
    raw = dehyphenate_linebreaks(raw)
    return normalize_text(raw)


def _has_letter_body(lines: List[PageLine]) -> bool:
    """
    Detect whether the current segment already looks like a real letter.
    """
    txt = _text_of(lines)
    return bool(SALUTATION_RE.search(txt) or SIGNATURE_RE.search(txt))


def _is_header_line(line: str) -> bool:
    """
    Detect whether a line looks like a letter header: place + date.
    """
    txt = normalize_text(line)

    if len(txt) > 160:
        return False

    return bool(HEADER_RE.search(txt))


def _next_lines_text(lines: List[PageLine], index: int, window: int = 6) -> str:
    return " ".join(
        normalize_text(lines[j].text)
        for j in range(index + 1, min(len(lines), index + 1 + window))
        if lines[j].text.strip()
    )


def _looks_like_address_block(lines: List[PageLine], index: int) -> bool:
    """
    Detect only explicit address blocks after a place/date line.

    Example:
        Višegrad 13. VII. 26.
        [Адреса:]
        Dr. Zdenka Marković
        ...
    """
    for j in range(index + 1, min(len(lines), index + 4)):
        txt = normalize_text(lines[j].text)
        if ADDRESS_RE.search(txt):
            return True

    return False


def _should_start_new_letter(
    current: List[PageLine],
    all_lines: List[PageLine],
    index: int,
) -> bool:
    """
    Decide whether the current header starts a new letter.

    Rules:
    - If there is no current segment, it cannot start a new split.
    - Consecutive or near-consecutive header variants belong to the same letter.
    - A header followed by an explicit address block is kept inside the current letter.
    - Otherwise, a new place/date header starts a new letter.
    """
    if not current:
        return False

    # Consecutive header variants belong to the same letter.
    # Example:
    #   Женева, 14. X 1930.
    #   Ženeva, 14 oktobra 1930 g.
    if len(current) <= 3 and not _has_letter_body(current):
        return False

    # Do not split if this place/date line is part of an address block.
    if _has_letter_body(current) and _looks_like_address_block(all_lines, index):
        return False

    return True


def split_lines_into_letters(lines: Iterable[PageLine]) -> List[LetterRecord]:
    """
    Split PAGE XML lines into individual letters.

    The function splits on place/date headers while avoiding false splits
    caused by duplicate header lines and address blocks.
    """
    current: List[PageLine] = []
    records: List[LetterRecord] = []

    line_list = list(lines)

    def flush():
        nonlocal current

        if not current:
            return

        text = _text_of(current)

        if not text.strip():
            current = []
            return

        pages = sorted({str(x.page_number) for x in current if x.page_number is not None})
        files = sorted({x.page_file for x in current})
        header = " | ".join([x.text for x in current[:8] if x.text.strip()])

        rid = f"letter_{len(records) + 1:04d}"

        records.append(
            LetterRecord(
                letter_id=rid,
                source_page_files=";".join(files),
                source_pages=";".join(pages),
                raw_header=header,
                text=text,
            )
        )

        current = []

    for i, line in enumerate(line_list):
        txt = normalize_text(line.text)
        header = _is_header_line(txt)

        if header and _should_start_new_letter(current, line_list, i):
            flush()
            current.append(line)
        else:
            current.append(line)

    flush()
    return records


def records_to_dicts(records: Iterable[LetterRecord]) -> List[Dict[str, str]]:
    return [asdict(r) for r in records]