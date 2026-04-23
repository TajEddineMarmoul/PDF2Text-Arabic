import fitz
from pdf2text_arabic._extract import _compute_clip

pdf_path = r"download/قانون-المالية-2023.pdf"
doc = fitz.open(pdf_path)

for p_num in [20, 21]:
    print(f"\n--- PAGE {p_num + 1} ---")
    page = doc[p_num]
    clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)
    
    # Try mixed with different snap_y_tolerance
    for tol in [3, 5, 10]:
        tabs = page.find_tables(vertical_strategy="lines", horizontal_strategy="text", clip=clip, snap_y_tolerance=tol)
        if tabs.tables:
            print(f"MIXED (lines/text) snap_y_tolerance={tol}: cols={len(tabs.tables[0].header.cells)}")
            ext = tabs.tables[0].extract()
            print(f"Row 10: {ext[10] if len(ext) > 10 else ''}")
