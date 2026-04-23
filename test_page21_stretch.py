import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic._tables import extract_tables

doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[20] # Page 21
clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)

print("--- TESTING PAGE 21 WITH CLIP + STRETCH ---")
# Manually simulate the fix in a test script
tabs = page.find_tables(clip=clip)
if tabs.tables:
    t = tabs.tables[0]
    print(f"Original bbox: {t.bbox}")
    # Stretch outer cells
    for row in t.rows:
        if row.cells:
            if row.cells[0]:
                row.cells[0] = (clip.x0, row.cells[0][1], row.cells[0][2], row.cells[0][3])
            if row.cells[-1]:
                row.cells[-1] = (row.cells[-1][0], row.cells[-1][1], clip.x1, row.cells[-1][3])
    
    ext = t.extract()
    found_rates = any("10" in str(row) or "2,5" in str(row) for row in ext)
    print(f"Found rates after stretch: {found_rates}")
    print(f"Example row: {ext[10] if len(ext)>10 else ''}")
else:
    print("No tables found.")
