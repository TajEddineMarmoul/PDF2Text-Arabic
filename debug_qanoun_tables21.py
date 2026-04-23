import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic._tables import _extract_cell_text

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
                    
        rawdict = page.get_text("rawdict", clip=clip)
        
        found_rates = False
        for ri, row in enumerate(t.rows):
            ext = []
            for ci, cell in enumerate(reversed(row.cells)):
                ext.append(_extract_cell_text(page, cell, rawdict=rawdict))
            
            # If the rightmost column (which is the last in visually RTL, meaning ext[-1] or ext[0])
            # wait, ext is reversed. So ext[-1] is the rightmost column?
            # Actually, ext[0] is the rightmost column in RTL? 
            # In RTL, reversed(row.cells) means ci=0 is the rightmost cell.
            # So ext[0] is the rightmost column.
            if ext[0].strip() in ["10", "8", "40", "2,5"]:
                print(f"Row {ri} matched rates: {ext}")
                found_rates = True
        
        if not found_rates:
            print("No rates found in the rightmost column!")
