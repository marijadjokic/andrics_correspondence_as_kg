#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path

import fitz  # PyMuPDF


def parse_pages(spec: str) -> list[int]:
    pages: list[int] = []

    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            pages.extend(range(int(a), int(b) + 1))
        else:
            pages.append(int(part))

    return pages


def extract_pages_as_image_pdf(
    input_pdf: str,
    pages: list[int],
    output_pdf: str,
    dpi: int = 300,
) -> None:
    src = fitz.open(input_pdf)
    out = fitz.open()

    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)

    for page_number in pages:
        idx = page_number - 1

        if idx < 0 or idx >= len(src):
            raise ValueError(
                f"Page {page_number} outside PDF range 1-{len(src)}"
            )

        page = src.load_page(idx)

        # Render page as image. This removes problematic embedded fonts/OCR layers.
        pix = page.get_pixmap(matrix=matrix, alpha=False, colorspace=fitz.csRGB)

        width_pt = pix.width * 72 / dpi
        height_pt = pix.height * 72 / dpi

        new_page = out.new_page(width=width_pt, height=height_pt)
        rect = fitz.Rect(0, 0, width_pt, height_pt)
        new_page.insert_image(rect, pixmap=pix)

    Path(output_pdf).parent.mkdir(parents=True, exist_ok=True)
    out.save(output_pdf, deflate=True, garbage=4)
    out.close()
    src.close()

    print(f"Wrote image-only PDF: {output_pdf}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Extract selected PDF pages as image-only PDF for Transkribus."
    )
    ap.add_argument("--pdf", required=True, help="Input PDF")
    ap.add_argument("--pages", required=True, help="1-based page spec, e.g. 4-9,12,15")
    ap.add_argument("--out", required=True, help="Output PDF")
    ap.add_argument("--dpi", type=int, default=300, help="Rendering DPI, default 300")

    args = ap.parse_args()

    extract_pages_as_image_pdf(
        input_pdf=args.pdf,
        pages=parse_pages(args.pages),
        output_pdf=args.out,
        dpi=args.dpi,
    )


if __name__ == "__main__":
    main()