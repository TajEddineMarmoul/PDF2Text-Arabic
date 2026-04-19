"""Debug visualization for the extraction pipeline.

Draws a page with overlays showing what ``extract_page`` actually sees:
table bboxes, OCR regions, and text blocks, numbered in the exact reading
order the extractor produces.  Because it calls the same
``order_reading_rtl`` the extractor uses, the labels are a faithful debug
view of the pipeline — if the numbering looks wrong, the output text is
wrong in the same way.
"""

from __future__ import annotations

from typing import Any, Literal

import fitz
from IPython.display import Image, display

from ._extract import (
    _PAGE_NUMBER_BOTTOM_PCT,
    _compute_clip,
    _image_only_regions,
    _is_page_number_text,
    detect_footer_y,
    order_reading_rtl,
)
from ._tables import extract_tables


def draw_page_layout(
    page: fitz.Page,
    *,
    dpi: int = 150,
    crop_top: float = 0,
    crop_bottom: float = 0,
    crop_unit: Literal["px", "pct"] = "px",
    auto_crop_top: bool = False,
    auto_crop_bottom: bool = False,
    detect_footer: bool = True,
) -> None:
    """Render *page* with extraction overlays and show it inline.

    Colours:
        * blue    — detected tables
        * magenta — OCR regions
        * orange  — full-width (spanning) text blocks
        * green   — right-column text
        * red     — left-column text
        * grey    — filtered page numbers (PN)

    When ``crop_top``/``crop_bottom`` are used (manual or auto), the trimmed
    header/footer bands are shaded grey so you can preview what will be dropped.
    Detected footer regions are shaded light blue.

    Labels are placed outside each rectangle in reading-order sequence.
    """
    w, h = page.rect.width, page.rect.height
    clip = _compute_clip(page, crop_top, crop_bottom, crop_unit, auto_crop_top, auto_crop_bottom)
    mid_x = w / 2

    # Shade cropped header/footer bands
    if clip.y0 > page.rect.y0:
        header_band = fitz.Rect(page.rect.x0, page.rect.y0, page.rect.x1, clip.y0)
        page.draw_rect(header_band, color=(0.6, 0.6, 0.6), fill=(0.85, 0.85, 0.85), fill_opacity=0.5, width=0.5)
    if clip.y1 < page.rect.y1:
        footer_band = fitz.Rect(page.rect.x0, clip.y1, page.rect.x1, page.rect.y1)
        page.draw_rect(footer_band, color=(0.6, 0.6, 0.6), fill=(0.85, 0.85, 0.85), fill_opacity=0.5, width=0.5)

    # Shade footer region
    if detect_footer:
        footer_y, guaranteed = detect_footer_y(page, clip)
        if footer_y is not None:
            # We don't adjust the clip here (so we see the blocks), but we shade the area
            f_rect = fitz.Rect(clip.x0, footer_y, clip.x1, clip.y1)
            page.draw_rect(f_rect, color=(0.2, 0.5, 0.9), fill=(0.7, 0.85, 1.0), fill_opacity=0.3, width=0.5)

    # 1. Detection — same primitives the extractor uses
    _, table_bbox_tuples = extract_tables(page, clip=clip)
    table_bboxes = [fitz.Rect(t) for t in table_bbox_tuples]
    ocr_regions = _image_only_regions(page, clip)

    raw: dict[str, Any] = page.get_text("rawdict")  # type: ignore[assignment]
    
    # Define zones for page number detection
    page_num_bottom_zone_y = clip.y1 - clip.height * _PAGE_NUMBER_BOTTOM_PCT
    page_num_top_zone_y = clip.y0 + clip.height * _PAGE_NUMBER_BOTTOM_PCT
    
    text_blocks: list[dict[str, Any]] = []
    page_num_blocks: list[dict[str, Any]] = []

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

        # Check if it's a page number block (top or bottom)
        block_text = "".join(
            c.get("c", "")
            for line in b.get("lines", [])
            for span in line.get("spans", [])
            for c in span.get("chars", [])
        ).strip()

        is_pn = (
            block_text
            and (cy >= page_num_bottom_zone_y or cy <= page_num_top_zone_y)
            and all(
                _is_page_number_text(
                    "".join(c.get("c", "") for c in span.get("chars", [])).strip()
                )
                for line in b.get("lines", [])
                for span in line.get("spans", [])
                if "".join(c.get("c", "") for c in span.get("chars", [])).strip()
            )
        )

        if is_pn:
            page_num_blocks.append(b)
        else:
            text_blocks.append(b)

    # 2. Unified item list
    all_items: list[dict[str, Any]] = []
    for t in table_bboxes:
        all_items.append({"bbox": t, "type": "TABLE"})
    for r in ocr_regions:
        all_items.append({"bbox": r, "type": "IMAGE"})
    for b in page_num_blocks:
        all_items.append({"bbox": fitz.Rect(b["bbox"]), "type": "PAGE_NUM"})
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
        elif it["type"] == "PAGE_NUM":
            color = (0.6, 0.6, 0.6)
        elif r.width > 0.55 * w:
            color = (1, 0.5, 0)
        elif (r.x0 + r.x1) / 2 > mid_x:
            color = (0, 0.7, 0)
        else:
            color = (0.8, 0, 0)

        page.draw_rect(r, color=color, width=2)

        if it["type"] == "PAGE_NUM":
            label = "PN"
        elif it["type"] != "TEXT":
            label = f"{it['type'][0]}{i + 1}"
        else:
            label = str(i + 1)

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
