"""Page-level and PDF-level Arabic text extraction."""

from __future__ import annotations

from typing import Literal

import fitz

from ._footer import detect_footer_y
from ._tables import extract_tables
from ._text import build_row_text, clean_arabic, merge_lines_by_y

fitz.TOOLS.set_small_glyph_heights(True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compute_clip(
    page_rect: fitz.Rect,
    crop_top: float,
    crop_bottom: float,
    crop_unit: Literal["px", "pct"],
) -> fitz.Rect:
    """Build a clip rectangle from crop parameters."""
    if crop_unit == "pct":
        h = page_rect.height
        top = page_rect.y0 + h * crop_top / 100
        bottom = page_rect.y1 - h * crop_bottom / 100
    else:
        top = page_rect.y0 + crop_top
        bottom = page_rect.y1 - crop_bottom
    return fitz.Rect(page_rect.x0, top, page_rect.x1, bottom)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_page(
    page,
    *,
    crop_top: float = 0,
    crop_bottom: float = 0,
    crop_unit: Literal["px", "pct"] = "px",
    detect_footer: bool = True,
) -> str:
    """Extract corrected Arabic text from one PyMuPDF page.

    Args:
        page: A ``fitz.Page`` object.
        crop_top: Amount to crop from the top (header area).
        crop_bottom: Amount to crop from the bottom (page-number area).
        crop_unit: ``"px"`` for points/pixels, ``"pct"`` for percentage of
            page height.
        detect_footer: When *True*, automatically detect a footnote separator
            line (``------``) and exclude everything below it.
    """
    clip = _compute_clip(page.rect, crop_top, crop_bottom, crop_unit)

    if detect_footer:
        footer_y = detect_footer_y(page, clip)
        if footer_y is not None:
            clip = fitz.Rect(clip.x0, clip.y0, clip.x1, footer_y - 1)

    table_entries, t_bboxes = extract_tables(page, clip=clip)

    rawdict = page.get_text("rawdict", clip=clip)
    pieces: list[tuple[float, str]] = []

    for block in rawdict["blocks"]:
        if "lines" not in block:
            continue

        bx0, by0, bx1, by1 = block["bbox"]
        in_table = False
        for tx0, ty0, tx1, ty1 in t_bboxes:
            bcx = (bx0 + bx1) / 2
            bcy = (by0 + by1) / 2
            if tx0 <= bcx <= tx1 and ty0 <= bcy <= ty1:
                in_table = True
                break
        if in_table:
            continue

        rows = merge_lines_by_y(block["lines"])
        rows.sort(key=lambda r: r["cy"])

        lines_text: list[str] = []
        for row in rows:
            text = build_row_text(row["spans"])
            text = clean_arabic(text).strip()
            if text:
                lines_text.append(text)

        if lines_text:
            pieces.append((by0, "\n".join(lines_text)))

    for y_top, ttext in table_entries:
        pieces.append((y_top, ttext))

    pieces.sort(key=lambda p: p[0])

    return "\n\n".join(text for _, text in pieces)


def extract_pdf(
    pdf_path: str,
    *,
    crop_top: float = 0,
    crop_bottom: float = 0,
    crop_unit: Literal["px", "pct"] = "px",
    detect_footer: bool = True,
) -> str:
    """Extract Arabic text from a PDF file.

    Args:
        pdf_path: Path to the PDF file.
        crop_top: Amount to crop from the top of every page.
        crop_bottom: Amount to crop from the bottom of every page.
        crop_unit: ``"px"`` for points/pixels, ``"pct"`` for percentage.
        detect_footer: Auto-detect footnote separator lines and crop below.

    Returns:
        The full extracted text with pages separated by double newlines.
    """
    doc = fitz.open(pdf_path)
    pages: list[str] = []
    for page in doc:
        text = extract_page(
            page,
            crop_top=crop_top,
            crop_bottom=crop_bottom,
            crop_unit=crop_unit,
            detect_footer=detect_footer,
        )
        if text.strip():
            pages.append(text)
    doc.close()
    return "\n\n".join(pages)
