"""Footer separator detection for Arabic PDF pages.

Detects footnote separator lines (horizontal rules) in the bottom portion
of a page and returns the y-coordinate to crop at.  Handles both vector
drawings (non-selectable lines) and text-based separators (selectable dashes).
"""

from __future__ import annotations

import fitz


def detect_footer_y(page, clip: fitz.Rect) -> float | None:
    """Find the y-coordinate of a footnote separator within *clip*.

    Searches the bottom 40% of the clipped area for:
    1. Horizontal vector lines/thin rects spanning ≥15% of page width
    2. Text lines consisting entirely of dash-like characters (≥3 chars)

    Returns the separator y so the caller can crop there, or ``None``.
    """
    page_height = clip.y1 - clip.y0
    if page_height <= 0:
        return None

    search_top = clip.y0 + page_height * 0.6  # only bottom 40%
    page_width = clip.x1 - clip.x0
    min_line_width = page_width * 0.15

    best_y: float | None = None

    # --- 1. Vector drawings: horizontal lines and thin rectangles ---
    for drawing in page.get_drawings():
        for item in drawing["items"]:
            if item[0] == "l":  # line segment
                p1, p2 = item[1], item[2]
                if abs(p1.y - p2.y) < 2:  # horizontal
                    w = abs(p2.x - p1.x)
                    y = (p1.y + p2.y) / 2
                    if y >= search_top and w >= min_line_width:
                        if best_y is None or y < best_y:
                            best_y = y
            elif item[0] == "re":  # thin rectangle acting as a line
                r = item[1]
                if r.height < 3 and r.width >= min_line_width and r.y0 >= search_top:
                    if best_y is None or r.y0 < best_y:
                        best_y = r.y0

    if best_y is not None:
        return best_y

    # --- 2. Text-based separators: rows of dashes/underscores ---
    text_data = page.get_text("dict", clip=clip)
    for block in text_data.get("blocks", []):
        if block.get("type") != 0 or "lines" not in block:
            continue
        for line in block["lines"]:
            text = "".join(span.get("text", "") for span in line["spans"])
            stripped = text.strip()
            if len(stripped) >= 3 and all(
                c in "-_\u2014\u2013\u2550\u2501" for c in stripped
            ):
                ly = line["bbox"][1]
                if ly >= search_top:
                    if best_y is None or ly < best_y:
                        best_y = ly

    return best_y
