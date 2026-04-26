"""Page-level and PDF-level Arabic text extraction."""

from __future__ import annotations

import logging
from pathlib import Path
from statistics import median
from dataclasses import dataclass
from typing import Any, Callable, Literal
import re
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

# Only treat a digit-only line as a page number when it sits inside the
# bottom ``_PAGE_NUMBER_BOTTOM_PCT`` fraction of the clip. Guards against
# dropping legitimate numeric body text higher up on the page.
_PAGE_NUMBER_BOTTOM_PCT = 0.12


def _is_page_number_text(text: str) -> bool:
    """True if *text* looks like a bare page number (e.g. ``-3-``, ``(١٢)``).

    Accepts any combination of digits (ASCII or Arabic-Indic) surrounded by
    punctuation/whitespace. Rejects anything containing a letter, so real
    body text like ``المادة 3`` is kept.
    """
    t = text.strip()
    if not t:
        return False
    if any(c.isalpha() for c in t):
        return False
    return any(c.isdigit() for c in t)


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


@dataclass
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
    sizes: list[float] = []
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
                txt = "".join(c.get("c", "") for c in span.get("chars", [])).strip()
                if not txt or not txt.strip():
                    continue
                sz = span.get("size", 0)
                if sz >= 20:  # skip headings
                    continue
                sizes.extend([sz] * len(txt))
    if not sizes:
        return 0
    return median(sizes)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_page_number_block(
    block: dict[str, Any], top_zone_y: float, bottom_zone_y: float
) -> bool:
    """Return True if the block contains only a page number and is located in the margins."""
    if "lines" not in block:
        return False

    r = fitz.Rect(block["bbox"])
    cy = (r.y0 + r.y1) / 2

    if top_zone_y < cy < bottom_zone_y:
        return False

    block_text = "".join(
        c.get("c", "")
        for line in block.get("lines", [])
        for span in line.get("spans", [])
        for c in span.get("chars", [])
    ).strip()

    if not block_text:
        return False

    return _is_page_number_text(block_text)


def _shares_words(text1: str, text2: str) -> bool:
    """Return True if text1 and text2 share at least 3 words, or 50% of their words."""
    t1 = re.sub(r"[^\w\s]", "", text1)
    t1 = re.sub(r"\d+", "", t1)
    t2 = re.sub(r"[^\w\s]", "", text2)
    t2 = re.sub(r"\d+", "", t2)

    w1 = set(t1.split())
    w2 = set(t2.split())

    if not w1 or not w2:
        return False

    overlap = len(w1 & w2)
    return overlap >= 3 or (overlap / len(w1) >= 0.5)


def _auto_detect_top_y(page: fitz.Page) -> float | None:
    """Scan the top margin for a page number or repeating header.

    Returns the boundary Y coordinate (plus a 5px margin) if the outermost
    text block or small logo is a page number or repeats across adjacent pages.
    """
    doc = page.parent
    rect = page.rect
    margin = rect.height * 0.15
    clip = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + margin)

    def get_top_blocks(p: fitz.Page):
        rawdict = p.get_text("rawdict", clip=clip)
        blocks = []
        for b in rawdict.get("blocks", []):
            if "lines" not in b:
                continue
            text = "".join(
                c.get("c", "")
                for l in b["lines"]
                for s in l["spans"]
                for c in s["chars"]
            ).strip()
            if not text:
                continue
            blocks.append(
                {
                    "text": text,
                    "bbox": b["bbox"],
                    "cy": (b["bbox"][1] + b["bbox"][3]) / 2,
                    "block": b,
                }
            )
        blocks.sort(key=lambda x: x["cy"])
        return blocks

    def get_top_images(p: fitz.Page):
        images = []
        try:
            for info in p.get_image_info(hashes=True):
                ir = fitz.Rect(info["bbox"])
                # Must be in the top margin AND be a small logo (< 20% of page height)
                # This protects against cropping full-page scanned images.
                if ir.y0 < clip.y1 and ir.height < rect.height * 0.2:
                    images.append(
                        {
                            "bbox": info["bbox"],
                            "cy": (ir.y0 + ir.y1) / 2,
                            "digest": info.get("digest"),
                        }
                    )
        except Exception:
            pass
        images.sort(key=lambda x: x["cy"])
        return images

    curr_blocks = get_top_blocks(page)
    curr_images = get_top_images(page)

    first_text = curr_blocks[0] if curr_blocks else None
    first_img = curr_images[0] if curr_images else None

    outermost_type = None
    if first_text and first_img:
        outermost_type = "text" if first_text["cy"] < first_img["cy"] else "image"
    elif first_text:
        outermost_type = "text"
    elif first_img:
        outermost_type = "image"

    if not outermost_type:
        return None

    if outermost_type == "text":
        curr_text = first_text["text"]
        # 1. Is it a standalone page number?
        if _is_page_number_block(first_text["block"], rect.y0 + margin, rect.y1):
            return first_text["bbox"][3] + 5

        # 2. Is it a repeating header?
        if doc:
            if page.number > 0:
                prev_blocks = get_top_blocks(doc[page.number - 1])
                if prev_blocks and _shares_words(curr_text, prev_blocks[0]["text"]):
                    return first_text["bbox"][3] + 5

            if page.number < len(doc) - 1:
                next_blocks = get_top_blocks(doc[page.number + 1])
                if next_blocks and _shares_words(curr_text, next_blocks[0]["text"]):
                    return first_text["bbox"][3] + 5

    elif outermost_type == "image":
        # 3. Is it a repeating image header?
        if doc and first_img.get("digest"):
            if page.number > 0:
                prev_images = get_top_images(doc[page.number - 1])
                if prev_images and prev_images[0].get("digest") == first_img["digest"]:
                    return first_img["bbox"][3] + 5

            if page.number < len(doc) - 1:
                next_images = get_top_images(doc[page.number + 1])
                if next_images and next_images[0].get("digest") == first_img["digest"]:
                    return first_img["bbox"][3] + 5

    return None


def _auto_detect_bottom_y(page: fitz.Page) -> float | None:
    """Scan the bottom margin of the page for a page number text.

    Returns the boundary Y coordinate (minus a 5px margin) if the outermost
    text block in the margin is a page number, else None.
    """
    rect = page.rect
    margin = rect.height * _PAGE_NUMBER_BOTTOM_PCT
    clip = fitz.Rect(rect.x0, rect.y1 - margin, rect.x1, rect.y1)

    rawdict = page.get_text("rawdict", clip=clip)
    valid_blocks = []

    for block in rawdict.get("blocks", []):
        if "lines" not in block:
            continue

        block_text = "".join(
            c.get("c", "")
            for line in block.get("lines", [])
            for span in line.get("spans", [])
            for c in span.get("chars", [])
        ).strip()

        if not block_text:
            continue

        cy = (block["bbox"][1] + block["bbox"][3]) / 2
        valid_blocks.append(
            {"text": block_text, "cy": cy, "bbox": block["bbox"], "block": block}
        )

    if not valid_blocks:
        return None

    valid_blocks.sort(key=lambda x: x["cy"])
    last_block = valid_blocks[-1]

    if _is_page_number_block(last_block["block"], rect.y0, rect.y1 - margin):
        return last_block["bbox"][1] - 5  # by0 - 5

    return None


def _compute_clip(
    page: fitz.Page,
    crop_top: float,
    crop_bottom: float,
    crop_unit: Literal["px", "pct"],
    auto_crop_top: bool = False,
    auto_crop_bottom: bool = False,
) -> fitz.Rect:
    """Build a clip rectangle from crop parameters, resolving auto-detection if requested."""
    page_rect = page.rect
    y0, y1 = page_rect.y0, page_rect.y1

    # Resolve Top
    manual_top = y0 + (
        page_rect.height * crop_top / 100 if crop_unit == "pct" else crop_top
    )
    resolved_top = manual_top
    if auto_crop_top:
        auto_y = _auto_detect_top_y(page)
        if auto_y is not None:
            resolved_top = auto_y

    # Resolve Bottom
    manual_bottom = y1 - (
        page_rect.height * crop_bottom / 100 if crop_unit == "pct" else crop_bottom
    )
    resolved_bottom = manual_bottom
    if auto_crop_bottom:
        auto_y = _auto_detect_bottom_y(page)
        if auto_y is not None:
            resolved_bottom = auto_y

    return fitz.Rect(page_rect.x0, resolved_top, page_rect.x1, resolved_bottom)


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
        ln for ln in raw.splitlines() if not _is_page_number_text(ln)
    ).strip()
    return len(meaningful) < _EMPTY_TEXT_THRESHOLD


def _merge_regions_safely(page: fitz.Page, regions: list[fitz.Rect]) -> list[fitz.Rect]:
    """Merge fragmented image boxes if the gap between them has no selectable text.

    This handles cases like 'khitab malak' where a single logical block of text
    is broken into dozens of tiny images.
    """
    if len(regions) < 2:
        return regions

    # Sort regions vertically
    sorted_regions = sorted(regions, key=lambda r: r.y0)
    merged: list[fitz.Rect] = []

    if not sorted_regions:
        return []

    current = fitz.Rect(sorted_regions[0])

    for i in range(1, len(sorted_regions)):
        next_rect = sorted_regions[i]

        # 1. Are they vertically close? (within 25 pixels)
        gap_height = next_rect.y0 - current.y1

        if gap_height < 25:
            # 2. Check the gap for selectable text
            # We create a box that spans the width of both and the height of the gap
            gap_box = fitz.Rect(
                min(current.x0, next_rect.x0),
                current.y1,
                max(current.x1, next_rect.x1),
                next_rect.y0,
            )

            # If the gap is tiny (overlap or < 2px), just merge
            if gap_height <= 2 or not page.get_text("text", clip=gap_box).strip():
                # Safe to merge
                current.include_rect(next_rect)
                continue

        # Not safe to merge or too far apart
        merged.append(current)
        current = fitz.Rect(next_rect)

    merged.append(current)

    # Final cleanup: If we still have many regions and the page is mostly empty,
    # just take the bounding box of everything.
    if len(merged) > 10:
        full_text = page.get_text("text").strip()
        if len(full_text) < _EMPTY_TEXT_THRESHOLD:
            # Page is essentially a puzzle of images with no text layer
            big_box = merged[0]
            for r in merged[1:]:
                big_box.include_rect(r)
            return [big_box]

    return merged


def _image_only_regions(page: fitz.Page, clip: fitz.Rect) -> list[fitz.Rect]:
    """Return surgical bboxes of regions that likely need OCR.

    It finds image placements within the clip, then subtracts the area
    occupied by any selectable text to ensure we only OCR the 'unreadable'
    parts of the page.
    """
    # 1. Find all selectable text blocks in the clip
    blocks: list[tuple[Any, ...]] = page.get_text("blocks", clip=clip)  # type: ignore[assignment]
    text_bboxes = [
        fitz.Rect(b[:4]) for b in blocks if b[6] == 0 and b[4].strip()  # type 0 is text
    ]

    regions: list[fitz.Rect] = []

    # 2. Inspect image objects
    image_infos: list[dict[str, Any]] = page.get_image_info()  # type: ignore[assignment]
    for img in image_infos:
        # FORCE strict intersection with our manual crop clip
        img_bbox = fitz.Rect(img["bbox"]) & clip

        # If the intersection is tiny (e.g., symbols, footnote markers, logos), skip it.
        # We increase this threshold to avoid sending 15x15 pixel asterisks to an expensive OCR LLM.
        if img_bbox.is_empty or img_bbox.width < 15 or img_bbox.height < 10:
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

    # 3. Merge fragmented regions safely
    return _merge_regions_safely(page, regions)


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
# Reading-order logic (shared with the debug visualization)
# ---------------------------------------------------------------------------


def order_reading_rtl(
    items: list,
    clip: fitz.Rect,
    *,
    bbox: Callable[[Any], fitz.Rect],
) -> list:
    """Sort *items* in RTL two-column reading order.

    The page is split into horizontal bands by full-width ("spanning") items.
    Within each columns band, items are grouped by column and the right column
    is emitted before the left (Arabic reading order).

    *items* is opaque; *bbox* is a callable returning a ``fitz.Rect`` for each
    item.  Returned list contains the same items in reading order.

    Used by both the extractor and the debug visualization so a single source
    of truth drives both.
    """
    w = clip.width
    mid_x = clip.x0 + w / 2

    # Gutter detection: vote where narrow blocks sit, pick the biggest empty
    # strip in the middle 40% as the column divider.
    density_map = [0] * (int(w) + 1)
    for it in items:
        r = bbox(it)
        if (r.x1 - r.x0) > (w * 0.6):
            continue
        s = int(max(0, r.x0 - clip.x0))
        e = int(min(w, r.x1 - clip.x0))
        for i in range(s, e):
            density_map[i] += 1
    search_start = int(w * 0.3)
    search_end = int(w * 0.7)
    middle = density_map[search_start:search_end]
    best_start, best_len, cur = 0, 0, -1
    for i, val in enumerate(middle):
        if val == 0:
            if cur == -1:
                cur = i
        elif cur != -1:
            gap = i - cur
            if gap > best_len:
                best_len, best_start = gap, cur
            cur = -1
    if cur != -1 and (len(middle) - cur) > best_len:
        best_len = len(middle) - cur
        best_start = cur
    if best_len >= 10:
        mid_x = clip.x0 + search_start + best_start + (best_len / 2)

    spanning, cols = [], []
    for it in items:
        r = bbox(it)
        bw = r.x1 - r.x0
        is_span = bw > 0.55 * w or (
            r.x0 < mid_x - 10 and r.x1 > mid_x + 10 and bw > 0.15 * w
        )
        (spanning if is_span else cols).append(it)

    spanning.sort(key=lambda x: bbox(x).y0)
    merged: list[dict[str, Any]] = []
    for it in spanning:
        r = bbox(it)
        if merged and r.y0 <= merged[-1]["y1"] + 10:
            merged[-1]["y1"] = max(merged[-1]["y1"], r.y1)
            merged[-1]["blocks"].append(it)
        else:
            merged.append({"y0": r.y0, "y1": r.y1, "blocks": [it]})

    bands: list[dict[str, Any]] = []
    cur_y = clip.y0
    for s in merged:
        if s["y0"] > cur_y:
            bands.append({"type": "columns", "y0": cur_y, "y1": s["y0"], "blocks": []})
        bands.append(
            {"type": "spanning", "y0": s["y0"], "y1": s["y1"], "blocks": s["blocks"]}
        )
        cur_y = s["y1"]
    if cur_y < clip.y1:
        bands.append({"type": "columns", "y0": cur_y, "y1": clip.y1, "blocks": []})

    for it in cols:
        r = bbox(it)
        cy = (r.y0 + r.y1) / 2
        assigned = False
        for band in bands:
            if band["type"] == "columns" and band["y0"] <= cy <= band["y1"]:
                band["blocks"].append(it)
                assigned = True
                break
        if not assigned:
            for band in bands:
                if (
                    band["type"] == "columns"
                    and band["y0"] - 10 <= cy <= band["y1"] + 10
                ):
                    band["blocks"].append(it)
                    break

    ordered: list = []
    for band in bands:
        if not band["blocks"]:
            continue
        if band["type"] == "spanning":
            band["blocks"].sort(key=lambda x: bbox(x).y0)
            ordered.extend(band["blocks"])
        else:
            rb, lb = [], []
            for x in band["blocks"]:
                r = bbox(x)
                (rb if (r.x0 + r.x1) / 2 > mid_x else lb).append(x)
            rb.sort(key=lambda x: bbox(x).y0)
            lb.sort(key=lambda x: bbox(x).y0)
            ordered.extend(rb)
            ordered.extend(lb)
    return ordered


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_page(
    page: fitz.Page,
    *,
    crop_top: float = 8.0,
    crop_bottom: float = 4.5,
    crop_unit: Literal["px", "pct"] = "pct",
    auto_crop_top: bool = True,
    auto_crop_bottom: bool = True,
    detect_footer: bool = True,
    on_empty: Literal["ignore", "warn", "ocr", "auto"] = "warn",
    table_strategy: str | None = None,
    gemini_model: str = DEFAULT_GEMINI_MODEL,
) -> tuple[str, dict | None]:
    """Extract corrected Arabic text from one PyMuPDF page.

    Returns (text, last_table_state).
    """
    # 1. INITIAL CROP
    clip = _compute_clip(
        page, crop_top, crop_bottom, crop_unit, auto_crop_top, auto_crop_bottom
    )

    # 1.5. PRE-EXTRACT TABLES
    kwargs: dict[str, Any] = {"clip": clip}
    if table_strategy is not None:
        kwargs["strategy"] = table_strategy

    tabs = page.find_tables(**kwargs)
    table_bboxes = [fitz.Rect(t.bbox) for t in tabs.tables]

    # Keep the geometric crop separate from footer cropping. Full-page OCR
    # should use only crop_top/crop_bottom/auto-crop, never footer detection.
    original_clip = fitz.Rect(clip)

    # 2. CONTENT DETECTION
    is_empty_selectable = _is_empty_page(page, original_clip)
    mixed_regions = _image_only_regions(page, original_clip)

    # USER REQUEST: If the page has ANY part that needs OCR (mixed_regions),
    # or if the page is completely empty, we upgrade the entire page to full OCR.
    # This prevents messy merging of PyMuPDF text and Gemini text.
    effective_mode = on_empty
    if on_empty == "auto" and (is_empty_selectable or mixed_regions):
        effective_mode = "ocr"

    # 3. FOOTER DETECTION
    footer_y = None

    if detect_footer and effective_mode != "ocr":
        footer_y, _ = detect_footer_y(page, clip, table_bboxes=table_bboxes)
        if footer_y is not None:
            apply_crop = True
            for ty0, ty1 in [(t.y0, t.y1) for t in table_bboxes]:
                if ty0 <= footer_y <= ty1:
                    apply_crop = False
                    break
            if apply_crop:
                # Shrink clip to exclude footer/reference text from extraction.
                clip = fitz.Rect(clip.x0, clip.y0, clip.x1, footer_y - 1)

    pieces: list[tuple[float, float, float, float, str]] = []
    last_table_state = None

    # 4. SELECTABLE EXTRACTION
    if effective_mode != "ocr":
        table_entries, t_bboxes, last_table_state = extract_tables(
            page, clip=clip, strategy=table_strategy
        )

        # Add Tables
        for (y_top, ttext), (tx0, ty0, tx1, ty1) in zip(table_entries, t_bboxes):
            pieces.append((y_top, ty1, tx0, tx1, ttext))

        # Add Text
        rawdict: dict[str, Any] = page.get_text("rawdict", clip=clip)
        body_size = _body_font_size(rawdict, t_bboxes)
        page_num_zone_y = clip.y1 - clip.height * _PAGE_NUMBER_BOTTOM_PCT

        for block in rawdict["blocks"]:
            if "lines" not in block:
                continue
            bx0, by0, bx1, by1 = block["bbox"]

            # Skip if inside a table
            if any(
                tx0 <= (bx0 + bx1) / 2 <= tx1 and ty0 <= (by0 + by1) / 2 <= ty1
                for tx0, ty0, tx1, ty1 in t_bboxes
            ):
                continue

            rows = merge_lines_by_y(block["lines"])
            rows.sort(key=lambda r: r["cy"])

            lines_text: list[str] = []
            for row in rows:
                # Mirror debug logic: filter out reference tips (superscripts)
                spans = [s for s in row["spans"] if not _is_superscript(s, body_size)]
                text = build_row_text(spans)
                text = clean_arabic(text).strip()
                if not text:
                    continue
                # Drop digit-only lines only when they sit in the bottom
                # page-number zone — keeps real numeric body text intact.
                if row["cy"] >= page_num_zone_y and _is_page_number_text(text):
                    continue
                lines_text.append(text)

            if lines_text:
                pieces.append((by0, by1, bx0, bx1, "\n".join(lines_text)))

    # 5. OCR EXTRACTION
    if effective_mode == "ocr":
        ocr_results = run_ocr(page, [original_clip], model=gemini_model)
        for y_top, ocr_text in ocr_results:
            pieces.append((original_clip.y0, original_clip.y1, original_clip.x0, original_clip.x1, ocr_text))

    # 6. FINAL RECONSTRUCTION
    if not pieces:
        return "", last_table_state

    final_reading_order = order_reading_rtl(
        pieces,
        clip,
        bbox=lambda p: fitz.Rect(p[2], p[0], p[3], p[1]),
    )

    return "\n\n".join(text for *_, text in final_reading_order), last_table_state


def extract_pdf(
    pdf_path: str,
    *,
    crop_top: float = 8.0,
    crop_bottom: float = 4.5,
    crop_unit: Literal["px", "pct"] = "pct",
    auto_crop_top: bool = True,
    auto_crop_bottom: bool = True,
    detect_footer: bool = True,
    on_empty: Literal["ignore", "warn", "ocr", "auto"] = "warn",
    table_strategy: str | None = None,
    gemini_model: str = DEFAULT_GEMINI_MODEL,
) -> str:
    return extract_pdf_result(
        pdf_path,
        crop_top=crop_top,
        crop_bottom=crop_bottom,
        crop_unit=crop_unit,
        auto_crop_top=auto_crop_top,
        auto_crop_bottom=auto_crop_bottom,
        detect_footer=detect_footer,
        on_empty=on_empty,
        table_strategy=table_strategy,
        gemini_model=gemini_model,
    ).text


def extract_pdf_result(
    pdf_path: str,
    *,
    crop_top: float = 8.0,
    crop_bottom: float = 4.5,
    crop_unit: Literal["px", "pct"] = "pct",
    auto_crop_top: bool = True,
    auto_crop_bottom: bool = True,
    detect_footer: bool = True,
    on_empty: Literal["ignore", "warn", "ocr", "auto"] = "warn",
    table_strategy: str | None = None,
    gemini_model: str = DEFAULT_GEMINI_MODEL,
) -> ExtractionResult:
    path = Path(pdf_path)
    if not path.exists() or not path.is_file():
        raise InvalidPDFPathError(f"PDF path not found: {pdf_path}")

    if on_empty in ("ocr", "auto"):
        if not gemini_available():
            raise OCRUnavailableError("OCR requested but 'google-genai' not installed.")
        if not load_gemini_api_key():
            raise OCRUnavailableError("GEMINI_API_KEY is not set.")

    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        raise InvalidPDFPathError(f"Could not open PDF: {pdf_path}") from exc

    pages, empty_pages, mixed_pages, warnings = [], [], [], []
    for page in doc:
        page_no = _page_number(page)
        clip = _compute_clip(
            page, crop_top, crop_bottom, crop_unit, auto_crop_top, auto_crop_bottom
        )
        is_empty = _is_empty_page(page, clip)
        is_mixed = (not is_empty) and _has_content_images(page, clip)

        text, _ = extract_page(
            page,
            crop_top=crop_top,
            crop_bottom=crop_bottom,
            crop_unit=crop_unit,
            auto_crop_top=auto_crop_top,
            auto_crop_bottom=auto_crop_bottom,
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
