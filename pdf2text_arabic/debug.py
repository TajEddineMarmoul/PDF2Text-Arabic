"""Debug visualization for the extraction pipeline.

Draws a page with overlays showing what ``extract_page`` actually sees:
table bboxes, OCR regions, and text blocks, numbered in the exact reading
order the extractor produces.  Because it calls the same
``order_reading_rtl`` the extractor uses, the labels are a faithful debug
view of the pipeline — if the numbering looks wrong, the output text is
wrong in the same way.
"""

from __future__ import annotations

from typing import Any

import fitz
from IPython.display import Image, display

from ._extract import _compute_clip, _image_only_regions, order_reading_rtl
from ._tables import extract_tables


def draw_page_layout(page: fitz.Page, *, dpi: int = 150) -> None:
    """Render *page* with extraction overlays and show it inline.

    Colours:
        * blue    — detected tables
        * magenta — OCR regions
        * orange  — full-width (spanning) text blocks
        * green   — right-column text
        * red     — left-column text

    Labels are placed outside each rectangle in reading-order sequence.
    """
    w, h = page.rect.width, page.rect.height
    clip = _compute_clip(page.rect, 0, 0, "px")
    mid_x = w / 2

    # 1. Detection — same primitives the extractor uses
    _, table_bbox_tuples = extract_tables(page, clip=clip)
    table_bboxes = [fitz.Rect(t) for t in table_bbox_tuples]
    ocr_regions = _image_only_regions(page, clip)

    raw: dict[str, Any] = page.get_text("rawdict")  # type: ignore[assignment]
    text_blocks: list[dict[str, Any]] = []
    for b in raw["blocks"]:
        if "lines" not in b:
            continue
        r = fitz.Rect(b["bbox"])
        cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
        # Match extract_page: center-point containment for tables
        if any(t.x0 <= cx <= t.x1 and t.y0 <= cy <= t.y1 for t in table_bboxes):
            continue
        if any(r.intersects(o_rect) for o_rect in ocr_regions):
            continue
        text_blocks.append(b)

    # 2. Unified item list
    all_items: list[dict[str, Any]] = []
    for t in table_bboxes:
        all_items.append({"bbox": t, "type": "TABLE"})
    for r in ocr_regions:
        all_items.append({"bbox": r, "type": "IMAGE"})
    for b in text_blocks:
        all_items.append({"bbox": fitz.Rect(b["bbox"]), "type": "TEXT"})

    # Same reading order as extract_page
    final_order = order_reading_rtl(all_items, clip, bbox=lambda x: x["bbox"])

    # 3. Draw
    FONT_SIZE = 6
    BG_H = 8
    for i, it in enumerate(final_order):
        r = it["bbox"]
        if it["type"] == "TABLE":
            color = (0, 0, 1)
        elif it["type"] == "IMAGE":
            color = (1, 0, 1)
        elif r.width > 0.55 * w:
            color = (1, 0.5, 0)
        elif (r.x0 + r.x1) / 2 > mid_x:
            color = (0, 0.7, 0)
        else:
            color = (0.8, 0, 0)

        page.draw_rect(r, color=color, width=2)

        label = f"{it['type'][0]}{i + 1}" if it["type"] != "TEXT" else str(i + 1)
        bg_w = 10 if len(label) <= 2 else 18

        # Place label outside the rectangle so it never covers content
        if r.y0 >= BG_H + 1:
            bg = fitz.Rect(r.x1 - bg_w, r.y0 - BG_H, r.x1, r.y0)
            text_y = r.y0 - 2
        else:
            bg = fitz.Rect(r.x1 - bg_w, r.y1, r.x1, r.y1 + BG_H)
            text_y = r.y1 + BG_H - 2

        page.draw_rect(bg, color=(1, 1, 1), fill=(1, 1, 1))
        page.insert_text(
            (bg.x0 + 1, text_y),
            label,
            color=(0, 0, 1),
            fontsize=FONT_SIZE,
            fontname="helv",
        )

    pix = page.get_pixmap(dpi=dpi)
    display(Image(data=pix.tobytes("png")))
