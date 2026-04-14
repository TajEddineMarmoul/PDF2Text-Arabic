"""Page-level and PDF-level Arabic text extraction."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import re
import tempfile
from typing import Any, Literal

import fitz

from ._footer import detect_footer_y
from ._ocr import (
    DEFAULT_GEMINI_MODEL,
    gemini_available,
    load_gemini_api_key,
    run_ocr,
)
from ._tables import extract_tables
from ._text import build_row_text, clean_arabic, merge_lines_by_y

fitz.TOOLS.set_small_glyph_heights(True)

log = logging.getLogger(__name__)

# Superscript detection: a digit-only span is treated as a footnote
# indicator when its font size is ≤ this fraction of the page's dominant
# body font size.  E.g. 0.75 means anything ≤ 75% of body size is super.
_SUPERSCRIPT_SIZE_RATIO = 0.85

# Absolute ceiling: never strip digit spans larger than this, even if the
# ratio check would flag them (guards against tiny-body-font edge cases).
_SUPERSCRIPT_ABS_CEIL = 13

# A page is considered "empty" (image-only) when its extractable text,
# after stripping page-number patterns like  -10- , has fewer characters
# than this threshold.
_EMPTY_TEXT_THRESHOLD = 30

_PAGE_NUMBER_RE = re.compile(r"^[\s\-–—]*\d+[\s\-–—]*$")

# --- Mixed-page (image-based content region) detection ---
# An image placement is treated as a "content block" that likely needs
# OCR when its intersection with the clip is:
#   * ≥ this fraction of clip area (smaller → decoration / icon, skipped)
_MIN_IMAGE_AREA_RATIO = 0.05
#   * AND ≤ this fraction of clip area
#     (larger → full-page background / watermark, skipped)
_BACKGROUND_AREA_RATIO = 0.85
#   * AND the number of extractable chars inside its bbox is below this
#     (above → body text overlaps the image, treat as decoration)
_IMAGE_TEXT_CHAR_THRESHOLD = 15


class PDFArabicError(Exception):
    """Base exception for pdf2text-arabic failures."""


class InvalidPDFPathError(PDFArabicError):
    """Raised when a PDF path is missing, invalid, or unreadable."""


class OCRUnavailableError(PDFArabicError):
    """Raised when OCR is requested but Gemini is not configured.

    Either ``google-genai`` is not installed or ``GEMINI_API_KEY`` is missing
    from the environment and ``.env`` file.
    """


@dataclass(slots=True)
class ExtractionResult:
    """Structured extraction result for AI and downstream automation.

    Attributes:
        text: Final extracted text from non-empty pages.
        pages_total: Number of pages in the input PDF.
        pages_with_text: Number of pages that produced non-empty text.
        empty_pages: 1-based page numbers that produced empty text.
        mixed_pages: 1-based page numbers that contain extractable text
            AND a rasterized image block whose content is NOT in the text
            layer (e.g. a table baked into an image). Under
            ``on_empty='warn'`` (default), these pages contribute an empty
            string to ``text`` so partial/missing content is not silently
            returned. Use ``on_empty='ignore'`` to get the text layer anyway.
        warnings: Machine-readable warning messages (``empty_page:N`` and
            ``mixed_page:N`` entries).
    """

    text: str
    pages_total: int
    pages_with_text: int
    empty_pages: list[int]
    mixed_pages: list[int]
    warnings: list[str]


def _is_superscript(span: dict[str, Any], body_size: float) -> bool:
    """Return True if *span* looks like a footnote superscript indicator.

    Uses a ratio of the page's dominant body font size so the detection
    adapts to any document regardless of its base font size.
    """
    sz = span.get("size", 0)
    if sz > _SUPERSCRIPT_ABS_CEIL:
        return False
    if body_size > 0 and sz > body_size * _SUPERSCRIPT_SIZE_RATIO:
        return False
    text = "".join(c.get("c", "") for c in span.get("chars", [])).strip()
    return len(text) > 0 and text.isdigit()


def _body_font_size(
    rawdict: dict[str, Any], t_bboxes: list[tuple[float, float, float, float]]
) -> float:
    """Determine the dominant body font size from non-table text blocks.

    Returns 0 if no usable text is found (caller should skip filtering).
    """
    size_chars: dict[int, int] = {}
    for block in rawdict.get("blocks", []):
        if "lines" not in block:
            continue
        bx0, by0, bx1, by1 = block["bbox"]
        # Skip blocks inside tables
        in_table = False
        for tx0, ty0, tx1, ty1 in t_bboxes:
            bcx = (bx0 + bx1) / 2
            bcy = (by0 + by1) / 2
            if tx0 <= bcx <= tx1 and ty0 <= bcy <= ty1:
                in_table = True
                break
        if in_table:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                txt = span.get("text", "")
                if not txt or not txt.strip():
                    continue
                sz = round(span.get("size", 0))
                if sz >= 20:  # skip headings
                    continue
                size_chars[sz] = size_chars.get(sz, 0) + len(txt)
    if not size_chars:
        return 0
    return max(size_chars.items(), key=lambda item: item[1])[0]


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


def _is_empty_page(page: fitz.Page, clip: fitz.Rect) -> bool:
    """Return True if *page* has no meaningful text (image-only / scanned).

    A page is empty when its text content (ignoring page-number patterns
    like ``-10-``) is shorter than ``_EMPTY_TEXT_THRESHOLD`` characters AND
    the page contains at least one image.
    """
    if not page.get_images():
        return False  # no images → normal text page (even if short)
    raw = page.get_text("text", clip=clip).strip()
    # Strip lines that look like page numbers
    meaningful = "\n".join(
        ln for ln in raw.splitlines() if not _PAGE_NUMBER_RE.match(ln)
    ).strip()
    return len(meaningful) < _EMPTY_TEXT_THRESHOLD


def _image_only_regions(page: fitz.Page, clip: fitz.Rect) -> list[fitz.Rect]:
    """Return surgical bboxes of regions that likely need OCR.

    It finds image placements within the clip, then subtracts the area
    occupied by any selectable text to ensure we only OCR the 'unreadable'
    parts of the page.
    """
    # 1. Find all selectable text blocks in the clip
    blocks: list[tuple[Any, ...]] = page.get_text("blocks", clip=clip)  # type: ignore[assignment]
    text_bboxes = [
        fitz.Rect(b[:4])
        for b in blocks
        if b[6] == 0 and b[4].strip()  # type 0 is text
    ]

    regions: list[fitz.Rect] = []

    # 2. Inspect image objects
    image_infos: list[dict[str, Any]] = page.get_image_info()  # type: ignore[assignment]
    for img in image_infos:
        # FORCE strict intersection with our manual crop clip
        img_bbox = fitz.Rect(img["bbox"]) & clip

        # If the intersection is tiny or empty (because it was cropped out), skip it
        if img_bbox.is_empty or img_bbox.width < 10 or img_bbox.height < 10:
            continue

        # If an image has significant text on top of it, we skip the OCR
        # path for this region to avoid double-extraction.
        selectable_inside = page.get_text("text", clip=img_bbox).strip()
        if len(selectable_inside) > _IMAGE_TEXT_CHAR_THRESHOLD:
            continue

        # SURGICAL STEP: Shrink the image bbox to avoid selectable fragments
        surgical_bbox = fitz.Rect(img_bbox)  # Create a fresh copy to modify

        for t_bbox in text_bboxes:
            # If a text block overlaps our candidate region, we subtract it
            if t_bbox.intersects(surgical_bbox):
                # If text is at the bottom, push the surgical bottom up
                if t_bbox.y0 > surgical_bbox.y0 + (surgical_bbox.height * 0.5):
                    surgical_bbox.y1 = min(surgical_bbox.y1, t_bbox.y0 - 1)
                # If text is at the top, push the surgical top down
                elif t_bbox.y1 < surgical_bbox.y0 + (surgical_bbox.height * 0.5):
                    surgical_bbox.y0 = max(surgical_bbox.y0, t_bbox.y1 + 1)

        # Final safety check: must be inside the clip and have valid size
        final_bbox = surgical_bbox & clip
        if not final_bbox.is_empty and final_bbox.width > 5 and final_bbox.height > 5:
            regions.append(final_bbox)

    return regions


def _has_content_images(page: fitz.Page, clip: fitz.Rect) -> bool:
    """Return True if *page* has at least one image-only content region."""
    return bool(_image_only_regions(page, clip))



def _page_number(page: fitz.Page) -> int:
    """Return a safe 1-based page number for logs and metadata."""
    number = getattr(page, "number", None)
    if isinstance(number, int) and number >= 0:
        return number + 1
    return 1


def get_capabilities() -> dict[str, Any]:
    """Return runtime capabilities for feature-aware callers.

    This helper is intended for agents and orchestration code to determine
    whether optional features like OCR are available before choosing options.
    """
    return {
        "tables": True,
        "footer_detection": True,
        "ocr": gemini_available() and bool(load_gemini_api_key()),
        "recommended_import": "from pdf2text_arabic import extract_pdf, extract_pdf_result",
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_page(
    page: fitz.Page,
    *,
    crop_top: float = 0,
    crop_bottom: float = 0,
    crop_unit: Literal["px", "pct"] = "px",
    detect_footer: bool = True,
    on_empty: Literal["ignore", "warn", "ocr", "auto"] = "warn",
    table_strategy: str | None = None,
    gemini_model: str = DEFAULT_GEMINI_MODEL,
) -> str:
    """Extract corrected Arabic text from one PyMuPDF page.

    Args:
        page: A ``fitz.Page`` object.
        crop_top: Amount to crop from the top (header area).
        crop_bottom: Amount to crop from the bottom (page-number area).
        crop_unit: ``"px"`` for points/pixels, ``"pct"`` for percentage of
            page height.
        detect_footer: When *True*, automatically detect a footnote separator
            line and exclude everything below it.
        on_empty: What to do when a page has images whose content is NOT in
            the text layer (``"ignore"``, ``"warn"``, ``"auto"``, or ``"ocr"``).
        table_strategy: Strategy for PyMuPDF table detection.
        gemini_model: Gemini model id used when ``on_empty="ocr"`` or ``"auto"``.
    """
    # 1. INITIAL CROP (Manual)
    # This is the 'No Matter What' area.
    clip = _compute_clip(page.rect, crop_top, crop_bottom, crop_unit)

    # 2. FOOTER DETECTION (Automatic)
    # We do this immediately so OCR regions don't include footnote text.
    footer_y = None
    if detect_footer:
        footer_y, guaranteed = detect_footer_y(page, clip)
        if footer_y is not None:
            apply_crop = True
            if not guaranteed:
                # Don't cut through tables
                kwargs: dict[str, Any] = {"clip": clip}
                if table_strategy is not None:
                    kwargs["strategy"] = table_strategy
                tabs = page.find_tables(**kwargs)
                for table in tabs.tables:
                    tx0, ty0, tx1, ty1 = table.bbox
                    if ty0 <= footer_y <= ty1:
                        apply_crop = False
                        break
            if apply_crop:
                clip = fitz.Rect(clip.x0, clip.y0, clip.x1, footer_y - 1)

    # 3. CONTENT DETECTION
    # Now we look for images ONLY within the final clipped/cropped area.
    is_empty_selectable = _is_empty_page(page, clip)
    mixed_regions = _image_only_regions(page, clip)

    pieces: list[tuple[float, str]] = []

    # 4. SELECTABLE EXTRACTION
    # Extract digital text from the clipped area.
    if on_empty != "ocr" and (on_empty == "auto" or not is_empty_selectable):
        table_entries, t_bboxes = extract_tables(
            page, clip=clip, strategy=table_strategy
        )

        # Add Tables
        for y_top, ttext in table_entries:
            pieces.append((y_top, ttext))

        # Add Text
        rawdict: dict[str, Any] = page.get_text("rawdict", clip=clip)  # type: ignore[assignment]
        body_size = _body_font_size(rawdict, t_bboxes)

        for block in rawdict["blocks"]:
            if "lines" not in block:
                continue

            bx0, by0, bx1, by1 = block["bbox"]

            # Skip if inside a detected table
            if any(
                tx0 <= (bx0 + bx1) / 2 <= tx1 and ty0 <= (by0 + by1) / 2 <= ty1
                for tx0, ty0, tx1, ty1 in t_bboxes
            ):
                continue

            rows = merge_lines_by_y(block["lines"])
            rows.sort(key=lambda r: r["cy"])

            lines_text: list[str] = []
            for row in rows:
                spans = [s for s in row["spans"] if not _is_superscript(s, body_size)]
                text = build_row_text(spans)
                text = clean_arabic(text).strip()

                # Filter out standalone page numbers
                if text and not _PAGE_NUMBER_RE.match(text):
                    lines_text.append(text)

            if lines_text:
                pieces.append((by0, "\n".join(lines_text)))

    # 5. OCR EXTRACTION
    # Only if requested and we found image-only areas.
    if on_empty == "auto":
        if mixed_regions:
            # Run surgical OCR on any detected image regions
            ocr_results = run_ocr(page, mixed_regions, model=gemini_model)
            for y_top, ocr_text in ocr_results:
                pieces.append((y_top, ocr_text))
    elif on_empty == "ocr":
        # Force full-page OCR of the cropped area regardless of text
        ocr_results = run_ocr(page, [clip], model=gemini_model)
        for y_top, ocr_text in ocr_results:
            pieces.append((y_top, ocr_text))

    # 6. FINAL RECONSTRUCTION
    pieces.sort(key=lambda p: p[0])
    return "\n\n".join(text for _, text in pieces)


def extract_pdf(
    pdf_path: str,
    *,
    crop_top: float = 0,
    crop_bottom: float = 0,
    crop_unit: Literal["px", "pct"] = "px",
    detect_footer: bool = True,
    on_empty: Literal["ignore", "warn", "ocr", "auto"] = "warn",
    table_strategy: str | None = None,
    gemini_model: str = DEFAULT_GEMINI_MODEL,
) -> str:
    """Extract Arabic text from a PDF file.

    Args:
        pdf_path: Path to the PDF file.
        crop_top: Amount to crop from the top of every page.
        crop_bottom: Amount to crop from the bottom of every page.
        crop_unit: ``"px"`` for points/pixels, ``"pct"`` for percentage.
        detect_footer: Auto-detect footnote separator lines and crop below.
        on_empty: How to handle image-only pages (``"ignore"``, ``"warn"``,
            ``"auto"``, or ``"ocr"``).
        table_strategy: Strategy for PyMuPDF table detection.
        gemini_model: Gemini model id used when ``on_empty="ocr"`` or ``"auto"``
            (requires ``GEMINI_API_KEY`` in environment or .env).

    Returns:
        The full extracted text with pages separated by double newlines.
    """
    return extract_pdf_result(
        pdf_path,
        crop_top=crop_top,
        crop_bottom=crop_bottom,
        crop_unit=crop_unit,
        detect_footer=detect_footer,
        on_empty=on_empty,
        table_strategy=table_strategy,
        gemini_model=gemini_model,
    ).text


def extract_pdf_result(
    pdf_path: str,
    *,
    crop_top: float = 0,
    crop_bottom: float = 0,
    crop_unit: Literal["px", "pct"] = "px",
    detect_footer: bool = True,
    on_empty: Literal["ignore", "warn", "ocr", "auto"] = "warn",
    table_strategy: str | None = None,
    gemini_model: str = DEFAULT_GEMINI_MODEL,
) -> ExtractionResult:
    """Extract Arabic text and return structured metadata.

    This is the preferred API for AI agents and automation because it includes
    predictable metadata in addition to plain text.
    """
    path = Path(pdf_path)
    if not path.exists() or not path.is_file():
        raise InvalidPDFPathError(f"PDF path not found: {pdf_path}")

    if on_empty in ("ocr", "auto"):
        if not gemini_available():
            raise OCRUnavailableError(
                "OCR requested (on_empty='ocr' or 'auto') but 'google-genai' is not installed. "
                "Install with: pip install google-genai python-dotenv"
            )
        if not load_gemini_api_key():
            raise OCRUnavailableError(
                "GEMINI_API_KEY is not set. Add it to your .env or environment."
            )

    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        raise InvalidPDFPathError(f"Could not open PDF: {pdf_path}") from exc

    pages: list[str] = []
    empty_pages: list[int] = []
    mixed_pages: list[int] = []
    warnings: list[str] = []

    for page in doc:
        page_no = _page_number(page)
        clip = _compute_clip(page.rect, crop_top, crop_bottom, crop_unit)
        is_empty = _is_empty_page(page, clip)
        is_mixed = (not is_empty) and _has_content_images(page, clip)

        text = extract_page(
            page,
            crop_top=crop_top,
            crop_bottom=crop_bottom,
            crop_unit=crop_unit,
            detect_footer=detect_footer,
            on_empty=on_empty,
            table_strategy=table_strategy,
            gemini_model=gemini_model,
        )

        if is_mixed:
            mixed_pages.append(page_no)
            warnings.append(f"mixed_page:{page_no}")

        if text.strip():
            pages.append(text)
        elif not is_mixed:
            empty_pages.append(page_no)
            warnings.append(f"empty_page:{page_no}")

    pages_total = len(doc)
    doc.close()

    return ExtractionResult(
        text="\n\n".join(pages),
        pages_total=pages_total,
        pages_with_text=len(pages),
        empty_pages=empty_pages,
        mixed_pages=mixed_pages,
        warnings=warnings,
    )
