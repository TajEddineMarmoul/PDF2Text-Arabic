import fitz
from pdf2text_arabic._tables import extract_tables
from pdf2text_arabic._extract import _compute_clip

pdf_path = r"download/قانون-المالية-2023.pdf"
doc = fitz.open(pdf_path)

for p_num in [20, 21]:
    print(f"\n--- PAGE {p_num + 1} ---")
    page = doc[p_num]
    clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)
    
    tabs_mixed = page.find_tables(vertical_strategy="lines", horizontal_strategy="text", clip=clip)
    if tabs_mixed.tables:
        t = tabs_mixed.tables[0]
        # Stretch outer cells
        for row in t.rows:
            if row.cells:
                if row.cells[0]:
                    row.cells[0] = (clip.x0, row.cells[0][1], row.cells[0][2], row.cells[0][3])
                if row.cells[-1]:
                    row.cells[-1] = (row.cells[-1][0], row.cells[-1][1], clip.x1, row.cells[-1][3])
                    
        ext = []
        rawdict = page.get_text("rawdict", clip=clip)
        from pdf2text_arabic._tables import _extract_cell_text
        for ci, cell in enumerate(reversed(t.rows[10].cells)):
            ext.append(_extract_cell_text(page, cell, rawdict=rawdict))
            
        print(f"Row 10 with stretched cells: {ext}")
