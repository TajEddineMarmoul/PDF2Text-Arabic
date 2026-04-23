import fitz
from pdf2text_arabic._extract import _compute_clip

pdf_path = r"download/قانون-المالية-2023.pdf"
doc = fitz.open(pdf_path)

for p_num in [20, 21]:
    print(f"\n--- PAGE {p_num + 1} ---")
    page = doc[p_num]
    clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)
    
    tabs = page.find_tables(vertical_strategy="text", horizontal_strategy="text", clip=clip)
    print(f"text/text strategy found {len(tabs.tables)} tables.")
    for i, t in enumerate(tabs.tables):
        print(f"  Table {i+1}: {len(t.rows)} rows, {len(t.header.cells)} cols. BBox: {t.bbox}")
        if t.rows:
            cells = t.rows[0].cells
            print(f"    First row cells: {len(cells)}")
            print(f"    First cell bbox: {cells[0]}")
            print(f"    Last cell bbox: {cells[-1]}")
