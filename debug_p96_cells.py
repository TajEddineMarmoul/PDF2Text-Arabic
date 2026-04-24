import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic._tables import extract_tables

doc = fitz.open(r"download/قانون-المالية-2023.pdf")

# Page 96 (index 95)
page = doc[95]
clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)

tabs = page.find_tables(clip=clip)
t = tabs.tables[0]

print(f"Table BBox: {t.bbox}")
print(f"Rows: {len(t.rows)}, Cols: {len(t.header.cells)}")

for ri, row in enumerate(t.rows[:5]):
    print(f"\n--- Row {ri} ---")
    ncells = len(row.cells)
    for ci, cell in enumerate(row.cells):
        print(f"  Col {ci}: {cell}")
