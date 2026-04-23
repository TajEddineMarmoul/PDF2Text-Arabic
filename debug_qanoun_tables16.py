import fitz
from pdf2text_arabic._extract import _compute_clip

pdf_path = r"download/قانون-المالية-2023.pdf"
doc = fitz.open(pdf_path)

for p_num in [20, 21]:
    print(f"\n--- PAGE {p_num + 1} ---")
    page = doc[p_num]
    clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)
    
    # Try explicitly passing the page margins as vertical lines to force PyMuPDF
    # to consider the space outside the table lines as valid columns!
    tabs = page.find_tables(
        vertical_strategy="lines", 
        horizontal_strategy="text", 
        clip=clip, 
        explicit_vertical_lines=[clip.x0 + 20, clip.x1 - 20]
    )
    if tabs.tables:
        t = tabs.tables[0]
        print(f"Table found: cols={len(t.header.cells)}")
        ext = t.extract()
        print(f"Row 10: {ext[10] if len(ext) > 10 else ''}")
    else:
        print("No tables found")
