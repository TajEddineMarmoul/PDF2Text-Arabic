import fitz
from pdf2text_arabic._extract import _compute_clip

pdf_path = r"download/قانون-المالية-2023.pdf"
doc = fitz.open(pdf_path)

for p_num in [20, 21]:
    print(f"\n--- PAGE {p_num + 1} ---")
    page = doc[p_num]
    clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)
    
    # Try passing horizontal lines to force PyMuPDF to find the 1-row table!
    tabs = page.find_tables(
        vertical_strategy="lines", 
        horizontal_strategy="lines", 
        clip=clip, 
        horizontal_lines=[clip.y0, clip.y1]
    )
    if tabs.tables:
        t = tabs.tables[0]
        print(f"Table found: {len(t.rows)} rows, cols={len(t.header.cells)}, BBox={t.bbox}")
    else:
        print("No tables found")
