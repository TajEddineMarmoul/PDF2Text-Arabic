"""Debug visualization for the extraction pipeline.

Draws a page with overlays showing what ``extract_page`` actually sees:
table bboxes, OCR regions, and text blocks, numbered in the exact reading
order the extractor produces.
"""

from __future__ import annotations

import re
from typing import Any, Literal

import fitz

from ._extract import (
    OcrStrategy,
    _PAGE_NUMBER_BOTTOM_PCT,
    _body_font_size,
    _compute_clip,
    _image_only_regions,
    _is_empty_page,
    _is_page_number_text,
    _is_superscript,
    _resolve_ocr_strategy,
    detect_footer_y,
    order_reading_rtl,
)
from ._tables import extract_tables
from ._text import looks_like_scrambled_arabic


def get_debug_pixmap(
    page: fitz.Page,
    *,
    dpi: int = 150,
    crop_top: float = 8.0,
    crop_bottom: float = 4.5,
    crop_unit: Literal["px", "pct"] = "pct",
    auto_crop_top: bool = True,
    auto_crop_bottom: bool = True,
    detect_footer: bool = True,
    ocr_strategy: OcrStrategy | None = None,
) -> fitz.Pixmap:
    """Perform layout analysis and return a Pixmap with debug overlays."""
    
    # 1. SETUP & CLIPPING (Shared with _extract.py)
    w, h = page.rect.width, page.rect.height
    clip = _compute_clip(page, crop_top, crop_bottom, crop_unit, auto_crop_top, auto_crop_bottom)
    mid_x = w / 2
    original_clip = fitz.Rect(clip)

    # Shade cropped header/footer bands (Grey)
    if clip.y0 > page.rect.y0:
        header_band = fitz.Rect(page.rect.x0, page.rect.y0, page.rect.x1, clip.y0)
        page.draw_rect(header_band, color=(0.6, 0.6, 0.6), fill=(0.85, 0.85, 0.85), fill_opacity=0.5, width=0.5)
    if clip.y1 < page.rect.y1:
        footer_band = fitz.Rect(page.rect.x0, clip.y1, page.rect.x1, page.rect.y1)
        page.draw_rect(footer_band, color=(0.6, 0.6, 0.6), fill=(0.85, 0.85, 0.85), fill_opacity=0.5, width=0.5)

    # 2. DETECTION
    _, table_bbox_tuples, _ = extract_tables(page, clip=clip)
    table_bboxes = [fitz.Rect(t) for t in table_bbox_tuples]
    ocr_regions = _image_only_regions(page, original_clip)
    is_empty_selectable = _is_empty_page(page, original_clip)
    is_scrambled_selectable = looks_like_scrambled_arabic(
        page.get_text("text", clip=original_clip)
    )
    strategy = _resolve_ocr_strategy(
        ocr_strategy=ocr_strategy,
        default="auto",
    )

    full_page_ocr = strategy == "force" or (
        strategy == "auto"
        and (is_empty_selectable or is_scrambled_selectable or bool(ocr_regions))
    )

    # Shaded Footer (Cyan)
    if detect_footer and not full_page_ocr:
        footer_y, _ = detect_footer_y(page, clip, table_bboxes=table_bboxes)
        if footer_y is not None:
            apply_crop = True
            for ty0, ty1 in [(t.y0, t.y1) for t in table_bboxes]:
                if ty0 <= footer_y <= ty1:
                    apply_crop = False
                    break
            if apply_crop:
                # Shade the unified footer/footnote area Cyan
                f_rect = fitz.Rect(clip.x0, footer_y, clip.x1, clip.y1)
                page.draw_rect(f_rect, color=(0, 0.6, 0.6), fill=(0.8, 1.0, 1.0), fill_opacity=0.3, width=0.5)
                # Adjust clip for subsequent item collection
                clip = fitz.Rect(clip.x0, clip.y0, clip.x1, footer_y - 1)

    raw: dict[str, Any] = page.get_text("rawdict", clip=clip)  # type: ignore[assignment]
    body_size = _body_font_size(raw, table_bbox_tuples)

    # 3. ITEM COLLECTION
    page_num_bottom_zone_y = page.rect.y1 - page.rect.height * _PAGE_NUMBER_BOTTOM_PCT
    text_items: list[dict[str, Any]] = []
    superscript_items: list[dict[str, Any]] = []

    for b in raw["blocks"]:
        if "lines" not in b: continue
        r = fitz.Rect(b["bbox"])
        cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
        
        if any(t.x0 <= cx <= t.x1 and t.y0 <= cy <= t.y1 for t in table_bboxes): continue
        if any(r.intersects(o_rect) for o_rect in ocr_regions): continue
            
        block_text = "".join(c.get("c", "") for line in b.get("lines", []) for span in line.get("spans", []) for c in span.get("chars", [])).strip()
        if block_text and cy >= page_num_bottom_zone_y and all(_is_page_number_text("".join(c.get("c", "") for c in span.get("chars", [])).strip()) for line in b.get("lines", []) for span in line.get("spans", []) if "".join(c.get("c", "") for c in span.get("chars", [])).strip()):
            continue

        normal_bbox = fitz.Rect()
        for line in b["lines"]:
            for span in line["spans"]:
                span_bbox = fitz.Rect(span["bbox"])
                if _is_superscript(span, body_size):
                    superscript_items.append({"bbox": span_bbox, "type": "SUPERSCRIPT"})
                else:
                    if normal_bbox.is_empty: normal_bbox = fitz.Rect(span_bbox)
                    else: normal_bbox = normal_bbox | span_bbox

        if not normal_bbox.is_empty:
            text_items.append({"bbox": normal_bbox, "type": "TEXT"})

    all_items: list[dict[str, Any]] = []
    for t in table_bboxes: all_items.append({"bbox": t, "type": "TABLE"})
    for r in ocr_regions: all_items.append({"bbox": r, "type": "IMAGE"})
    all_items.extend(text_items)
    all_items.extend(superscript_items)

    final_order = order_reading_rtl(all_items, clip, bbox=lambda x: x["bbox"])

    trigger_index = None
    if full_page_ocr and strategy == "auto":
        for idx, item in enumerate(final_order):
            if item["type"] == "IMAGE":
                trigger_index = idx
                break
        if trigger_index is None and (is_empty_selectable or is_scrambled_selectable):
            trigger_index = 0

    # 4. DRAWING
    FONT_SIZE = 6
    BG_H = 8

    draw_order = final_order
    if full_page_ocr:
        # Full-page OCR discards PyMuPDF text/table boxes, so showing them
        # would make the debug image look like those boxes were used.
        draw_order = []

    for i, it in enumerate(draw_order):
        r = it["bbox"]
        if it["type"] == "TABLE": color = (0, 0, 1) # Blue
        elif it["type"] == "IMAGE": color = (1, 0, 1) # Magenta
        elif it["type"] == "SUPERSCRIPT": color = (0.5, 0, 0) # Maroon
        elif r.width > 0.55 * w: color = (1, 0.5, 0) # Orange
        elif (r.x0 + r.x1) / 2 > mid_x: color = (0, 0.7, 0) # Green
        else: color = (0.8, 0, 0) # Red

        width = 1 if it["type"] == "SUPERSCRIPT" else 2
        page.draw_rect(r, color=color, width=width)

        label = f"S{i+1}" if it["type"] == "SUPERSCRIPT" else (f"{it['type'][0]}{i+1}" if it["type"] != "TEXT" else str(i+1))
        bg_w = 10 if len(label) <= 2 else 18

        if r.y0 >= BG_H + 1:
            bg = fitz.Rect(r.x1 - bg_w, r.y0 - BG_H, r.x1, r.y0)
            text_y = r.y0 - 2
        else:
            bg = fitz.Rect(r.x1 - bg_w, r.y1, r.x1, r.y1 + BG_H)
            text_y = r.y1 + BG_H - 2

        page.draw_rect(bg, color=(1, 1, 1), fill=(1, 1, 1))
        page.insert_text((bg.x0 + 1, text_y), label, color=(0, 0, 1), fontsize=FONT_SIZE, fontname="helv")

    if full_page_ocr:
        page.draw_rect(
            original_clip,
            color=(1, 0, 1),
            fill=(1, 0, 1),
            fill_opacity=0.08,
            width=3,
        )
        if trigger_index is not None and final_order:
            trigger = final_order[trigger_index]
            trigger_box = trigger["bbox"]
            page.draw_rect(trigger_box, color=(1, 0, 0), width=3)
            label = (
                "FULL PAGE OCR - scrambled text layer"
                if is_scrambled_selectable
                else "FULL PAGE OCR - triggered here"
            )
            label_y = max(original_clip.y0 + 14, trigger_box.y0 - 10)
        elif strategy == "force":
            label = "FULL PAGE OCR - forced"
            label_y = original_clip.y0 + 14
        elif is_scrambled_selectable:
            label = "FULL PAGE OCR - scrambled text layer"
            label_y = original_clip.y0 + 14
        else:
            label = "FULL PAGE OCR - empty/selectable text missing"
            label_y = original_clip.y0 + 14
        label_box = fitz.Rect(original_clip.x0 + 8, label_y - 12, original_clip.x0 + 210, label_y + 4)
        page.draw_rect(label_box, color=(1, 1, 1), fill=(1, 1, 1))
        page.insert_text((label_box.x0 + 3, label_y), label, color=(1, 0, 0), fontsize=8, fontname="helv")

    return page.get_pixmap(dpi=dpi)


def draw_page_layout(
    page: fitz.Page,
    **kwargs,
) -> None:
    """Render *page* with extraction overlays and show it inline."""
    from IPython.display import Image, display

    pix = get_debug_pixmap(page, **kwargs)
    display(Image(data=pix.tobytes("png")))
