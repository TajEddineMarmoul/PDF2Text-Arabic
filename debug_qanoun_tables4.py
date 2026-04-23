import fitz
from pdf2text_arabic._tables import extract_tables
from pdf2text_arabic._extract import _compute_clip

pdf_path = r"download/قانون-المالية-2023.pdf"
doc = fitz.open(pdf_path)

for p_num in [20, 21]:
    print(f"\n--- PAGE {p_num + 1} ---")
    page = doc[p_num]
    clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)
    
    # 2. mixed_tabs (lines/text) - the one currently used
    tabs_mixed = page.find_tables(vertical_strategy="lines", horizontal_strategy="text", clip=clip)
    print("MIXED (lines/text):")
    if tabs_mixed.tables:
        t = tabs_mixed.tables[0]
        ext = t.extract()
        print("Row 0:", ext[0])
        print("Row 10:", ext[10] if len(ext)>10 else "")
            
    # 3. text/text
    tabs_text = page.find_tables(vertical_strategy="text", horizontal_strategy="text", clip=clip)
    print("TEXT/TEXT:")
    if tabs_text.tables:
        t = tabs_text.tables[0]
        ext = t.extract()
        print("Row 0:", ext[0])
        print("Row 10:", ext[10] if len(ext)>10 else "")
