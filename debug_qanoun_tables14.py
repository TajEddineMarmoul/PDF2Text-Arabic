import fitz
from pdf2text_arabic._extract import _compute_clip

pdf_path = r"download/قانون-المالية-2023.pdf"
doc = fitz.open(pdf_path)

for p_num in [20, 21]:
    print(f"\n--- PAGE {p_num + 1} ---")
    page = doc[p_num]
    clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)
    
    # min_words_vertical=0
    tabs_mixed = page.find_tables(vertical_strategy="lines", horizontal_strategy="text", clip=clip, min_words_vertical=0)
    print("MIXED with min_words_vertical=0:")
    if tabs_mixed.tables:
        print(f"cols={len(tabs_mixed.tables[0].header.cells)}")
        ext = tabs_mixed.tables[0].extract()
        print(f"Row 10: {ext[10] if len(ext) > 10 else ''}")
    else:
        print("No tables found.")
