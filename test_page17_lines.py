import fitz
from pdf2text_arabic._extract import _compute_clip

doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[16] # Page 17
clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)

print("--- PAGE 17 WITH vertical_strategy='lines' ---")
tabs = page.find_tables(clip=clip, vertical_strategy="lines", horizontal_strategy="text")
if tabs.tables:
    for i, t in enumerate(tabs.tables):
        print(f"Table {i+1} bbox: {t.bbox}, rows: {len(t.rows)}, cols: {len(t.header.cells)}")
else:
    print("No tables found.")
