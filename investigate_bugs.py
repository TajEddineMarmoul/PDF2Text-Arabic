import fitz
from pdf2text_arabic._extract import extract_page, _compute_clip

doc = fitz.open(r"download/قانون-المالية-2023.pdf")

pages_to_investigate = [8, 16, 17, 18, 20, 21, 46, 53, 54, 57] # Pages 9, 17, 18, 19, 21, 22, 47, 54, 55, 58

for p_num in pages_to_investigate:
    page = doc[p_num]
    clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)
    
    # 1. Check what PyMuPDF sees
    tabs = page.find_tables(clip=clip)
    
    print(f"\n--- PAGE {p_num+1} DIAGNOSIS ---")
    if not tabs.tables:
        print("  - Result: No tables detected by PyMuPDF default strategy.")
    else:
        for i, t in enumerate(tabs.tables):
            print(f"  - Table {i+1}: BBox={t.bbox}, Rows={len(t.rows)}, Cols={len(t.header.cells)}")
            if len(t.rows) == 1:
                print("    [!] WARNING: Detected as a 1-row table (Potential grouping error)")
    
    # 2. Check the final extraction
    text, _ = extract_page(page)
    table_lines = [l for l in text.split('\n') if '|' in l]
    print(f"  - Extracted: {len(table_lines)} table-formatted rows.")
    
    if p_num == 54: # Check 55
         print(f"  - Page 55 Snippet: {repr(text[:100])}")
