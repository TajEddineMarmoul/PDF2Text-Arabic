import fitz
from pdf2text_arabic._extract import _compute_clip

doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[53] # Page 54
clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)

tabs = page.find_tables(clip=clip)
t = tabs.tables[0]
x0 = max(clip.x0, t.bbox[0] - 10)
x1 = min(clip.x1, t.bbox[2] + 10)
y0 = max(clip.y0, t.bbox[1] - 50)
col_clip = fitz.Rect(x0, y0, x1, clip.y1)

mixed_tabs = page.find_tables(vertical_strategy="lines", horizontal_strategy="text", clip=col_clip)
if mixed_tabs.tables:
    for mt in mixed_tabs.tables:
        print(f"Mixed table: {mt.bbox}, rows={len(mt.rows)}")
        for r in mt.rows:
            print(f"Row: {r.bbox}")
