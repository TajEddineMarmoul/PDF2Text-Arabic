import fitz
from pdf2text_arabic._extract import _compute_clip

doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[53] # Page 54
clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)

tabs = page.find_tables(clip=clip)
if tabs.tables:
    t = tabs.tables[0]
    print(f"Table bbox: {t.bbox}")
    for i, row in enumerate(t.rows):
        print(f"Row {i}:")
        for j, cell in enumerate(row.cells):
            print(f"  Cell {j}: {cell}")
