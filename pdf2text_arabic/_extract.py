"""Page-level and PDF-level Arabic text extraction."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import re
from typing import Literal

import fitz

from ._footer import detect_footer_y
from ._tables import extract_tables
from ._text import build_row_text, clean_arabic, merge_lines_by_y

fitz.TOOLS.set_small_glyph_heights(True)

log = logging.getLogger(__name__)

# Superscript detection: a digit-only span is treated as a footnote
# indicator when its font size is ≤ this fraction of the page's dominant
# body font size.  E.g. 0.75 means anything ≤ 75% of body size is super.
_SUPERSCRIPT_SIZE_RATIO = 0.75

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
    """Raised when OCR is requested but unavailable in the runtime."""


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


def _is_superscript(span: dict, body_size: float) -> bool:
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


def _body_font_size(rawdict: dict, t_bboxes: list[tuple]) -> float:
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


def _is_empty_page(page, clip: fitz.Rect) -> bool:
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


def _image_only_regions(page, clip: fitz.Rect) -> list[fitz.Rect]:
    """Return clip-clamped bboxes of images that look like image-based
    content blocks (e.g. a rasterized table or figure whose text is NOT
    in the text layer).

    An image placement is included when its clip-clamped bbox:
      * covers between ``_MIN_IMAGE_AREA_RATIO`` and ``_BACKGROUND_AREA_RATIO``
        of the clip area (filters decoration and full-page backgrounds), AND
      * contains fewer than ``_IMAGE_TEXT_CHAR_THRESHOLD`` extractable chars
        inside (no text layer overlapping the image).
    """
    clip_area = clip.width * clip.height
    if clip_area <= 0:
        return []
    regions: list[fitz.Rect] = []
    for img in page.get_image_info(xrefs=True):
        bbox = fitz.Rect(img["bbox"]) & clip
        if bbox.is_empty or bbox.width <= 0 or bbox.height <= 0:
            continue
        ratio = (bbox.width * bbox.height) / clip_area
        if ratio < _MIN_IMAGE_AREA_RATIO or ratio > _BACKGROUND_AREA_RATIO:
            continue
        # Note: do not reuse a pre-built textpage here — PyMuPDF ignores the
        # ``clip`` argument when a ``textpage`` is supplied, returning the
        # full page text and defeating the sub-clip check.
        text_inside = page.get_text("text", clip=bbox).strip()
        if len(text_inside) < _IMAGE_TEXT_CHAR_THRESHOLD:
            regions.append(bbox)
    return regions


def _has_content_images(page, clip: fitz.Rect) -> bool:
    """Return True if *page* has at least one image-only content region."""
    return bool(_image_only_regions(page, clip))


def _ocr_image_regions(
    page,
    regions: list[fitz.Rect],
    language: str,
    dpi: int = 300,
) -> list[tuple[float, str]]:
    """OCR each image region independently and return ``(y_top, text)`` pairs.

    Renders each region to a pixmap at *dpi*, runs Tesseract via PyMuPDF's
    ``Pixmap.pdfocr_tobytes``, extracts the resulting text, and applies
    ``clean_arabic`` to fix RTL ordering. Empty results are dropped.
    """
    results: list[tuple[float, str]] = []
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    for region in regions:
        try:
            pix = page.get_pixmap(clip=region, matrix=mat)
            ocr_pdf = pix.pdfocr_tobytes(compress=False, language=language)
            ocr_doc = fitz.open("pdf", ocr_pdf)
            raw = ocr_doc[0].get_text("text").strip()
            ocr_doc.close()
        except Exception as exc:
            log.warning(
                "Page %d: OCR failed on image region %s: %s",
                _page_number(page),
                tuple(round(x, 1) for x in region),
                exc,
            )
            continue
        # Drop page-number-looking lines, keep the rest; apply RTL cleanup.
        lines = [
            clean_arabic(ln).strip()
            for ln in raw.splitlines()
            if ln.strip() and not _PAGE_NUMBER_RE.match(ln)
        ]
        cleaned = "\n".join(ln for ln in lines if ln)
        if cleaned:
            results.append((region.y0, cleaned))
    return results


def _ocr_page(page, clip: fitz.Rect, language: str = "ara") -> str:
    """Try to OCR *page* using Tesseract via PyMuPDF.

    Returns extracted text, or empty string if Tesseract is not available
    or OCR yields nothing.
    """
    try:
        tp = page.get_textpage_ocr(flags=0, language=language, full=True)
        text = page.get_text("text", clip=clip, textpage=tp).strip()
        # Strip page-number lines
        lines = [ln for ln in text.splitlines() if not _PAGE_NUMBER_RE.match(ln)]
        return "\n".join(lines).strip()
    except Exception as exc:
        log.warning("OCR failed on page %d: %s", _page_number(page), exc)
        return ""


def _page_number(page) -> int:
    """Return a safe 1-based page number for logs and metadata."""
    number = getattr(page, "number", None)
    if isinstance(number, int) and number >= 0:
        return number + 1
    return 1


def get_capabilities() -> dict[str, bool | str]:
    """Return runtime capabilities for feature-aware callers.

    This helper is intended for agents and orchestration code to determine
    whether optional features like OCR are available before choosing options.
    """
    return {
        "tables": True,
        "footer_detection": True,
        "ocr": hasattr(fitz.Page, "get_textpage_ocr"),
        "recommended_import": "from pdf2text_arabic import extract_pdf, extract_pdf_result",
    }


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
    on_empty: Literal["ignore", "warn", "ocr"] = "warn",
    ocr_language: str = "ara",
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
            the text layer (fully image-only pages, OR mixed pages with a
            rasterized table/figure alongside extractable text):
            ``"ignore"`` — silently return the extractable text layer
            (image content is lost without notice).
            ``"warn"`` — log a warning AND return empty string (since the
            page has missing content, we refuse to hand back a partial
            result; callers can switch to ``"ignore"`` to get the text layer
            anyway).
            ``"ocr"`` — attempt OCR via Tesseract; if that still yields
            nothing, log a warning and return empty string.
        ocr_language: Tesseract language code(s) for OCR (default ``"ara"``).
    """
    clip = _compute_clip(page.rect, crop_top, crop_bottom, crop_unit)

    # --- Empty / image-only page detection ---
    if _is_empty_page(page, clip):
        page_num = _page_number(page)
        if on_empty == "ocr":
            ocr_text = _ocr_page(page, clip, language=ocr_language)
            if ocr_text:
                return ocr_text
            log.warning("Page %d: image-only, OCR returned no text", page_num)
            return ""
        if on_empty == "warn":
            log.warning("Page %d: image-only, no extractable text", page_num)
        return ""

    # --- Mixed page detection: extractable text + image-based content block ---
    mixed_regions = _image_only_regions(page, clip)
    if mixed_regions:
        page_num = _page_number(page)
        if on_empty == "warn":
            log.warning(
                "Page %d: contains image-based content (e.g. rasterized table) "
                "that is NOT in the text layer — returning empty, use "
                "on_empty='ignore' to get the text layer anyway",
                page_num,
            )
            return ""
        # ``ignore`` → mixed_regions is ignored, only the text layer is returned.
        # ``ocr``    → OCR each region and splice into pieces after body loop.
        if on_empty != "ocr":
            mixed_regions = []

    if detect_footer:
        footer_y, guaranteed = detect_footer_y(page, clip)
        if footer_y is not None:
            apply_crop = True
            if not guaranteed:
                # Safety: table borders can look like footer separators.
                # Skip when superscript-guaranteed (footnote zones can be
                # falsely matched as "tables" by find_tables).
                tabs = page.find_tables(clip=clip)
                for table in tabs.tables:
                    tx0, ty0, tx1, ty1 = table.bbox
                    if ty0 <= footer_y <= ty1:
                        apply_crop = False
                        break
            if apply_crop:
                clip = fitz.Rect(clip.x0, clip.y0, clip.x1, footer_y - 1)

    table_entries, t_bboxes = extract_tables(page, clip=clip)

    rawdict = page.get_text("rawdict", clip=clip)
    body_size = _body_font_size(rawdict, t_bboxes)
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
            spans = [s for s in row["spans"] if not _is_superscript(s, body_size)]
            text = build_row_text(spans)
            text = clean_arabic(text).strip()
            if text:
                lines_text.append(text)

        if lines_text:
            pieces.append((by0, "\n".join(lines_text)))

    for y_top, ttext in table_entries:
        pieces.append((y_top, ttext))

    # Splice in OCR'd image-only regions (mixed-page path)
    if mixed_regions:
        # Re-clamp regions to the (possibly footer-trimmed) clip so we don't
        # OCR into a region that has since been cropped out.
        final_regions = [
            (r & clip) for r in mixed_regions if not (r & clip).is_empty
        ]
        for y_top, ocr_text in _ocr_image_regions(
            page, final_regions, language=ocr_language
        ):
            pieces.append((y_top, ocr_text))

    pieces.sort(key=lambda p: p[0])

    return "\n\n".join(text for _, text in pieces)


def extract_pdf(
    pdf_path: str,
    *,
    crop_top: float = 0,
    crop_bottom: float = 0,
    crop_unit: Literal["px", "pct"] = "px",
    detect_footer: bool = True,
    on_empty: Literal["ignore", "warn", "ocr"] = "warn",
    ocr_language: str = "ara",
) -> str:
    """Extract Arabic text from a PDF file.

    Args:
        pdf_path: Path to the PDF file.
        crop_top: Amount to crop from the top of every page.
        crop_bottom: Amount to crop from the bottom of every page.
        crop_unit: ``"px"`` for points/pixels, ``"pct"`` for percentage.
        detect_footer: Auto-detect footnote separator lines and crop below.
        on_empty: How to handle image-only pages (``"ignore"``, ``"warn"``,
            or ``"ocr"``).
        ocr_language: Tesseract language code(s) for OCR (default ``"ara"``).

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
        ocr_language=ocr_language,
    ).text


def extract_pdf_result(
    pdf_path: str,
    *,
    crop_top: float = 0,
    crop_bottom: float = 0,
    crop_unit: Literal["px", "pct"] = "px",
    detect_footer: bool = True,
    on_empty: Literal["ignore", "warn", "ocr"] = "warn",
    ocr_language: str = "ara",
) -> ExtractionResult:
    """Extract Arabic text and return structured metadata.

    This is the preferred API for AI agents and automation because it includes
    predictable metadata in addition to plain text.
    """
    path = Path(pdf_path)
    if not path.exists() or not path.is_file():
        raise InvalidPDFPathError(f"PDF path not found: {pdf_path}")

    if on_empty == "ocr" and not hasattr(fitz.Page, "get_textpage_ocr"):
        raise OCRUnavailableError(
            "OCR requested (on_empty='ocr') but runtime OCR support is unavailable"
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
        # Classify the page BEFORE extraction so we can report mixed pages
        # even when extract_page() returns "" under on_empty='warn'.
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
            ocr_language=ocr_language,
        )

        if is_mixed:
            mixed_pages.append(page_no)
            warnings.append(f"mixed_page:{page_no}")

        if text.strip():
            pages.append(text)
        elif not is_mixed:
            # Truly empty: either scanned page or image-only. Mixed pages
            # that return "" under warn are tracked separately above.
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
