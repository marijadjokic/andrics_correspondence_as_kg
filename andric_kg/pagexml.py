from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from lxml import etree

from .utils import normalize_text


@dataclass
class PageLine:
    page_file: str
    page_number: Optional[int]
    region_id: Optional[str]
    line_id: Optional[str]
    text: str


def _local_name(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _get_unicode_text(elem) -> Optional[str]:
    for child in elem.iter():
        if _local_name(child.tag) == "Unicode" and child.text:
            return normalize_text(child.text)
    return None


def parse_pagexml_file(xml_path: str | Path) -> List[PageLine]:
    """Extract text lines from a PAGE XML file exported by Transkribus.

    Namespace versions differ between PAGE XML releases; this parser uses local names.
    """
    xml_path = Path(xml_path)
    tree = etree.parse(str(xml_path))
    root = tree.getroot()

    page_number = None
    page_elems = [e for e in root.iter() if _local_name(e.tag) == "Page"]
    if page_elems:
        image_filename = page_elems[0].get("imageFilename", "")
        m = re.search(r"(\d+)", image_filename)
        if m:
            page_number = int(m.group(1))

    lines: List[PageLine] = []
    current_region = None
    for elem in root.iter():
        lname = _local_name(elem.tag)
        if lname == "TextRegion":
            current_region = elem.get("id")
        elif lname == "TextLine":
            text = _get_unicode_text(elem)
            if text:
                lines.append(
                    PageLine(
                        page_file=xml_path.name,
                        page_number=page_number,
                        region_id=current_region,
                        line_id=elem.get("id"),
                        text=text,
                    )
                )
    return lines


def parse_pagexml_dir(pagexml_dir: str | Path) -> List[PageLine]:
    pagexml_dir = Path(pagexml_dir)
    files = sorted(pagexml_dir.rglob("*.xml"))
    all_lines: List[PageLine] = []
    for file in files:
        try:
            all_lines.extend(parse_pagexml_file(file))
        except Exception as exc:
            print(f"WARNING: Could not parse {file}: {exc}")
    return all_lines


def lines_to_text(lines: Iterable[PageLine]) -> str:
    return "\n".join(line.text for line in lines if line.text).strip()
