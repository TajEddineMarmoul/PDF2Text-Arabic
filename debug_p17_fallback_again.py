import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic._tables import extract_tables

doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[16] # Page 17
clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)

tabs = page.find_tables(clip=clip)
t = tabs.tables[0]

# Simulate targeted fallback exactly as in _tables.py
p_width = page.rect.width
t_width = t.bbox[2] - t.bbox[0]

if t_width > p_width * 0.5:
    x0, x1 = page.rect.x0, page.rect.x1
else:
    x0, x1 = max(clip.x0, t.bbox[0] - 20), min(clip.x1, t.bbox[2] + 20)

col_clip = fitz.Rect(x0, clip.y0, x1, clip.y1)
print(f"col_clip: {col_clip}")

mixed_tabs = page.find_tables(vertical_strategy="lines", horizontal_strategy="text", clip=col_clip)
print(f"Fallback found {len(mixed_tabs.tables)} tables")
if mixed_tabs.tables:
    for mt in mixed_tabs.tables:
        print(f"  Fallback Table: rows={len(mt.rows)}, cols={len(mt.header.cells)}, bbox={mt.bbox}")
        if len(mt.header.cells) >= len(t.header.cells) and len(mt.rows) > len(t.rows) + 2:
            if abs(mt.bbox[0] - t.bbox[0]) < 100:
                print("    -> ACCEPTED BY STABILITY GATE")
            else:
                print("    -> REJECTED BY BBOX CHECK")
        else:
            print("    -> REJECTED BY COLS/ROWS CHECK")

