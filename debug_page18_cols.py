import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic._tables import extract_tables

doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[17] # page 18
clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)

tabs = page.find_tables(clip=clip)
if tabs.tables:
    for i, t in enumerate(tabs.tables):
        print(f"Table {i+1}: bbox={t.bbox}, rows={len(t.rows)}, cols={len(t.header.cells)}")
        if t.rows:
            ext = t.extract()
            print(f"Row 1 cells count: {len(ext[0])}")
            print(f"Row 1: {ext[1]}") # row 0 might be header
else:
    print("No tables found.")
