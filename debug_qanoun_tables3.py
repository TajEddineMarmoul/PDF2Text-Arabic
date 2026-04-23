import fitz
from pdf2text_arabic._tables import extract_tables
from pdf2text_arabic._extract import _compute_clip

pdf_path = r"download/قانون-المالية-2023.pdf"
doc = fitz.open(pdf_path)

for p_num in [20, 21]:
    print(f"\n--- PAGE {p_num + 1} ---")
    page = doc[p_num]
    clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)
    
    # 1. Default
    tabs_default = page.find_tables(clip=clip)
    print("DEFAULT:")
    for t in tabs_default.tables:
        print(f"  bbox: {t.bbox}, rows: {len(t.rows)}, cols: {len(t.header.cells)}")
        if t.rows:
            print(f"  First row: {[c for c in t.extract()[0]]}")

    # 2. mixed_tabs (lines/text) - the one currently used
    tabs_mixed = page.find_tables(vertical_strategy="lines", horizontal_strategy="text", clip=clip)
    print("MIXED (lines/text):")
    for t in tabs_mixed.tables:
        print(f"  bbox: {t.bbox}, rows: {len(t.rows)}, cols: {len(t.header.cells)}")
        if t.rows:
            print(f"  First row: {[c for c in t.extract()[0]]}")
            
    # 3. text/text
    tabs_text = page.find_tables(vertical_strategy="text", horizontal_strategy="text", clip=clip)
    print("TEXT/TEXT:")
    for t in tabs_text.tables:
        print(f"  bbox: {t.bbox}, rows: {len(t.rows)}, cols: {len(t.header.cells)}")
        if t.rows:
            print(f"  First row: {[c for c in t.extract()[0]]}")

