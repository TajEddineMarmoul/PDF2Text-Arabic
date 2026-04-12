"""Footer separator detection for Arabic PDF pages.

Detects the boundary between body text and footnotes using two strategies:

1. **Font-size analysis** – Body text in legal PDFs typically uses a larger
   font (e.g. 16 pt) while footnotes use a smaller font (e.g. 13–14 pt).
   The first sustained transition to smaller text in the lower portion of
   the page marks the footer boundary.

2. **Superscript fallback** – If font-size analysis finds nothing but
   superscript footnote indicators (small digit-only spans ≤10 pt) exist
   outside table regions, the topmost such superscript in the bottom 50 %
   of the page is used as the footer boundary.  This catches cases where
   body and footnote fonts are too close in size for strategy 1.
"""

from __future__ import annotations

import fitz

# Heading sizes are excluded when determining the body font size.
_HEADING_SIZE_MIN = 20

# Superscript ratio: a digit span is a superscript when its size is
# ≤ this fraction of the page's dominant body font size.
_SUPERSCRIPT_SIZE_RATIO = 0.85

# Absolute ceiling for superscript detection (same as _extract.py).
_SUPERSCRIPT_ABS_CEIL = 13


def _page_body_size(data: dict) -> float:
    """Compute the dominant body font size from rawdict data.

    Returns 0 when no usable text is found.
    """
    size_chars: dict[int, int] = {}
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                txt = "".join(c.get("c", "") for c in span.get("chars", [])).strip()
                if not txt:
                    continue
                sz = round(span.get("size", 0))
                if sz >= _HEADING_SIZE_MIN:
                    continue
                size_chars[sz] = size_chars.get(sz, 0) + len(txt)
    if not size_chars:
        return 0
    return max(size_chars.items(), key=lambda item: item[1])[0]


def _find_superscript_footer_y(page, clip: fitz.Rect) -> float | None:
    """Return the y of the topmost superscript digit in the bottom half.

    Uses a ratio of the page's dominant body font size so the detection
    adapts to any document.

    Returns ``None`` when no qualifying superscript is found.
    """
    page_height = clip.y1 - clip.y0
    if page_height <= 0:
        return None
    search_top = clip.y0 + page_height * 0.5  # bottom 50 %

    data = page.get_text("rawdict", clip=clip, flags=fitz.TEXT_PRESERVE_WHITESPACE)
    body_size = _page_body_size(data)
    if body_size <= 0:
        return None

    threshold = body_size * _SUPERSCRIPT_SIZE_RATIO
    best_y: float | None = None

    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                sz = span.get("size", 0)
                if sz > _SUPERSCRIPT_ABS_CEIL or sz > threshold:
                    continue
                txt = "".join(c.get("c", "") for c in span.get("chars", [])).strip()
                if not txt or not txt.isdigit():
                    continue
                sy = span["bbox"][1]
                if sy < search_top:
                    continue
                if best_y is None or sy < best_y:
                    best_y = sy

    return best_y


def _find_footnote_by_superscript_digits(page, clip: fitz.Rect) -> float | None:
    """Strategy 3: find the footer boundary by matching superscript digits to
    footnote reference lines.

    1. Scan the entire page for digit-only spans that are significantly smaller
       than the body font (superscript indicators like 55, 56, 57 at 10.6 pt).
    2. Collect their digit *values* (e.g. {"55", "56", "57"}).
    3. Scan lines top-to-bottom for lines whose text starts with one of those
       values followed by a dash ``-``.  These are footnote reference lines
       (e.g. ``55 - أنظر المادة35``).
    4. Return the y of the topmost such line.

    Returns ``None`` when no qualifying match is found.
    """
    data = page.get_text("rawdict", clip=clip, flags=fitz.TEXT_PRESERVE_WHITESPACE)
    body_size = _page_body_size(data)
    if body_size <= 0:
        return None

    threshold = body_size * _SUPERSCRIPT_SIZE_RATIO

    # Step 1: collect superscript digit values
    superscript_values: set[str] = set()
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                sz = span.get("size", 0)
                if sz > _SUPERSCRIPT_ABS_CEIL or sz > threshold:
                    continue
                txt = "".join(c.get("c", "") for c in span.get("chars", [])).strip()
                if txt and txt.isdigit():
                    superscript_values.add(txt)

    if not superscript_values:
        return None

    # Step 2: aggregate text by y-coordinate, then find footnote lines.
    # In rawdict, a single visual line (e.g. "55 - أنظر المادة35") can be
    # split across multiple ``line`` objects sharing the same y.  We group
    # by rounded y and concatenate.
    y_texts: dict[int, tuple[float, str]] = {}  # rounded_y → (exact_y, text)
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            exact_y = line["bbox"][1]
            ry = round(exact_y)
            for span in line.get("spans", []):
                chunk = "".join(
                    c.get("c", "") for c in span.get("chars", [])
                ).strip()
                if chunk:
                    if ry in y_texts:
                        prev_y, prev_txt = y_texts[ry]
                        y_texts[ry] = (min(prev_y, exact_y), prev_txt + " " + chunk)
                    else:
                        y_texts[ry] = (exact_y, chunk)

    best_y: float | None = None
    for _ry, (exact_y, full_text) in y_texts.items():
        full_text = full_text.strip()
        for val in superscript_values:
            if not full_text.startswith(val):
                continue
            rest = full_text[len(val):].lstrip()
            if rest.startswith("-") or rest.startswith("\u2013"):
                if best_y is None or exact_y < best_y:
                    best_y = exact_y
                break

    return best_y


def detect_footer_y(page, clip: fitz.Rect) -> tuple[float | None, bool]:
    """Find the y-coordinate where footnotes begin within *clip*.

    Strategy 1 – font-size analysis (fast, works when body/footnote sizes
    differ clearly).  Strategy 2 – superscript fallback when strategy 1
    returns *None* but superscript digit-only spans (significantly smaller
    than body text) are found in the bottom half of the page.  Strategy 3 –
    superscript-correlated: collects superscript digit *values* from the
    body, then finds footnote reference lines that start with those values
    followed by a dash.

    Returns ``(y, guaranteed)`` where *guaranteed* is ``True`` when the
    footer was found via strategy 2 or 3 (reliable indicators).  When
    *guaranteed* the caller should skip the table-overlap safety check
    because footnote areas can be falsely detected as \"tables\" by
    ``find_tables()``.
    """
    y = _detect_footer_by_fontsize(page, clip)
    if y is not None:
        return y, False

    # Strategy 3: superscript digit values → matching footnote lines
    y = _find_footnote_by_superscript_digits(page, clip)
    if y is not None:
        return y, True

    # Strategy 2 fallback: superscript indicator in bottom half
    y = _find_superscript_footer_y(page, clip)
    if y is not None:
        return y, True

    return None, False


# ------------------------------------------------------------------
# Strategy 1: font-size analysis
# ------------------------------------------------------------------


def _detect_footer_by_fontsize(page, clip: fitz.Rect) -> float | None:
    """Detect footer via sustained font-size transition."""
    page_height = clip.y1 - clip.y0
    if page_height <= 0:
        return None

    top_cutoff = clip.y0 + page_height * 0.5
    search_top = clip.y0 + page_height * 0.4  # search bottom 60 %

    # --- Collect per-line info ---
    data = page.get_text("dict", clip=clip)
    top_size_chars: dict[int, int] = {}
    lines: list[tuple[float, int, int]] = []  # (y, dominant_size, char_count)

    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            y = line["bbox"][1]
            size_chars: dict[int, int] = {}
            total = 0
            for span in line["spans"]:
                txt = span.get("text", "").strip()
                if txt:
                    sz = round(span["size"])
                    size_chars[sz] = size_chars.get(sz, 0) + len(txt)
                    total += len(txt)
            if total < 2:
                continue
            dominant = max(size_chars.items(), key=lambda item: item[1])[0]
            lines.append((y, dominant, total))
            if y < top_cutoff:
                for sz, n in size_chars.items():
                    top_size_chars[sz] = top_size_chars.get(sz, 0) + n

    if not top_size_chars or len(lines) < 3:
        return None

    # --- Determine body font size (exclude headings) ---
    body_candidates = {
        sz: n for sz, n in top_size_chars.items() if sz < _HEADING_SIZE_MIN
    }
    if not body_candidates:
        return None  # page only has headings — skip
    body_size = max(body_candidates.items(), key=lambda item: item[1])[0]
    threshold = body_size * 0.90

    # --- Find transition to smaller font in the search area ---
    lines.sort(key=lambda x: x[0])
    for i, (y, sz, _n) in enumerate(lines):
        if y < search_top:
            continue
        if sz >= threshold:
            continue
        # Candidate: verify that most text below is small-font
        remaining = lines[i:]
        small_chars = sum(n for _, s, n in remaining if s < threshold)
        total_chars = sum(n for _, _, n in remaining)
        if total_chars > 0 and small_chars / total_chars >= 0.70:
            return y

    return None
