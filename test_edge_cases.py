import glob
import os
import fitz
from pdf2text_arabic._extract import (
    _compute_clip, _auto_detect_top_y, _auto_detect_bottom_y,
    _image_only_regions, detect_footer_y, _PAGE_NUMBER_BOTTOM_PCT,
    _is_page_number_text, order_reading_rtl, _is_page_number_block
)
from pdf2text_arabic._tables import extract_tables

OUT_DIR = "output/edge_cases"
os.makedirs(OUT_DIR, exist_ok=True)

# Clear old images
for f in glob.glob(f"{OUT_DIR}/*.png"):
    os.remove(f)

def test_pdf_edge_cases(pdf_path):
    doc = fitz.open(pdf_path)
    pdf_name = os.path.basename(pdf_path).replace('.pdf', '')
    print(f"\nAnalyzing: {pdf_name}")
    
    # Test first 3 pages and the last page
    pages_to_test = list(set([0, 1, 2, len(doc)-1]))
    pages_to_test.sort()
    
    table_state = None
    for p_num in range(len(doc)):
        page = doc[p_num]

        # Apply current best defaults
        clip = _compute_clip(page, crop_top=8.0, crop_bottom=4.5, crop_unit="pct", auto_crop_top=True, auto_crop_bottom=True)

        # 1. Detect Tables (carrying state)
        _, table_bbox_tuples, table_state = extract_tables(page, clip=clip, prev_table_state=table_state)

        # Only draw and log if it's one of our targeted pages
        if p_num not in pages_to_test:
            continue

        top_y = clip.y0
        bottom_y = clip.y1

        h = page.rect.height
        print(f"  Page {p_num+1}:")
        print(f"    Final Top Y: {top_y:.1f} ({(top_y/h)*100:.1f}% of page)")
        print(f"    Final Bottom Y: {bottom_y:.1f} ({(bottom_y/h)*100:.1f}% of page)")

        # 2. Draw the debug layout and save to PNG
        dpi = 100
        w = page.rect.width
        mid_x = w / 2

        # Draw crops
        if clip.y0 > page.rect.y0:
            header_band = fitz.Rect(page.rect.x0, page.rect.y0, page.rect.x1, clip.y0)
            page.draw_rect(header_band, color=(0.6, 0.6, 0.6), fill=(0.85, 0.85, 0.85), fill_opacity=0.5, width=0.5)
        if clip.y1 < page.rect.y1:
            footer_band = fitz.Rect(page.rect.x0, clip.y1, page.rect.x1, page.rect.y1)
            page.draw_rect(footer_band, color=(0.6, 0.6, 0.6), fill=(0.85, 0.85, 0.85), fill_opacity=0.5, width=0.5)

        table_bboxes = [fitz.Rect(t) for t in table_bbox_tuples]
        
        ocr_regions = _image_only_regions(page, clip)
        needs_ocr = bool(ocr_regions)

        print(f"    Needs OCR: {needs_ocr}")
        print(f"    Tables: {len(table_bboxes)}")


        # Footer detection (Smart)
        footer_y, guaranteed = detect_footer_y(page, clip, table_bboxes=table_bboxes)
        if footer_y is not None:
            apply_crop = True
            for ty0, ty1 in [(t.y0, t.y1) for t in table_bboxes]:
                if ty0 <= footer_y <= ty1:
                    apply_crop = False
                    break
            if apply_crop:
                print(f"    Footer detected at Y={footer_y:.1f}")
                f_rect = fitz.Rect(clip.x0, footer_y, clip.x1, clip.y1)
                page.draw_rect(f_rect, color=(0.2, 0.5, 0.9), fill=(0.7, 0.85, 1.0), fill_opacity=0.3, width=0.5)
                clip = fitz.Rect(clip.x0, clip.y0, clip.x1, footer_y - 1)

        raw = page.get_text("rawdict", clip=clip)
        page_num_bottom_zone_y = page.rect.y1 - page.rect.height * _PAGE_NUMBER_BOTTOM_PCT
        
        text_blocks = []
        for b in raw.get("blocks", []):
            if "lines" not in b: continue
            cx, cy = (b["bbox"][0] + b["bbox"][2]) / 2, (b["bbox"][1] + b["bbox"][3]) / 2
            if any(t.x0 <= cx <= t.x1 and t.y0 <= cy <= t.y1 for t in table_bboxes): continue
            r = fitz.Rect(b["bbox"])
            if any(r.intersects(o_rect) for o_rect in ocr_regions): continue
            
            block_text = "".join(c.get("c", "") for l in b.get("lines", []) for s in l.get("spans", []) for c in s.get("chars", [])).strip()
            if (block_text and cy >= page_num_bottom_zone_y and 
                all(_is_page_number_text("".join(c.get("c", "") for c in s.get("chars", [])).strip()) 
                    for l in b.get("lines", []) for s in l.get("spans", []) 
                    if "".join(c.get("c", "") for c in s.get("chars", [])).strip())):
                continue
            text_blocks.append(b)

        all_items = [{"bbox": t, "type": "TABLE"} for t in table_bboxes]
        all_items.extend([{"bbox": r, "type": "IMAGE"} for r in ocr_regions])
        all_items.extend([{"bbox": fitz.Rect(b["bbox"]), "type": "TEXT"} for b in text_blocks])

        final_order = order_reading_rtl(all_items, clip, bbox=lambda x: x["bbox"])

        FONT_SIZE = 6
        BG_H = 8
        for i, it in enumerate(final_order):
            r = it["bbox"]
            if it["type"] == "TABLE": color = (0, 0, 1)
            elif it["type"] == "IMAGE": color = (1, 0, 1)
            elif r.width > 0.55 * w: color = (1, 0.5, 0)
            elif (r.x0 + r.x1) / 2 > mid_x: color = (0, 0.7, 0)
            else: color = (0.8, 0, 0)

            page.draw_rect(r, color=color, width=2)
            label = f"{it['type'][0]}{i + 1}" if it["type"] != "TEXT" else str(i + 1)
            bg_w = 10 if len(label) <= 2 else 18
            if r.y0 >= BG_H + 1:
                bg = fitz.Rect(r.x1 - bg_w, r.y0 - BG_H, r.x1, r.y0)
                text_y = r.y0 - 2
            else:
                bg = fitz.Rect(r.x1 - bg_w, r.y1, r.x1, r.y1 + BG_H)
                text_y = r.y1 + BG_H - 2

            page.draw_rect(bg, color=(1, 1, 1), fill=(1, 1, 1))
            page.insert_text((bg.x0 + 1, text_y), label, color=(0, 0, 1), fontsize=FONT_SIZE, fontname="helv")

        pix = page.get_pixmap(dpi=dpi)
        out_file = os.path.join(OUT_DIR, f"{pdf_name}_p{p_num+1}.png")
        pix.save(out_file)

    doc.close()

for p in glob.glob("download/*.pdf"):
    test_pdf_edge_cases(p)

print(f"\nDone! All debug images saved to {OUT_DIR}/")
