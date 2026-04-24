import fitz
from pdf2text_arabic._extract import extract_page, _compute_clip
from pdf2text_arabic._tables import extract_tables

doc = fitz.open(r"download/قانون-المالية-2023.pdf")

pages_to_check = [59, 60, 61, 95, 106]

for p_num in pages_to_check:
    print(f"\n{'='*20} PAGE {p_num+1} {'='*20}")
    
    page = doc[p_num]
    clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)
    
    # Check default PyMuPDF tables
    tabs = page.find_tables(clip=clip)
    print(f"Default PyMuPDF tables found: {len(tabs.tables)}")
    for i, t in enumerate(tabs.tables):
        print(f"  Table {i+1}: BBox={t.bbox}, Cols={len(t.header.cells)}, Rows={len(t.rows)}")
    
    # Check our full extraction
    text, state = extract_page(page)
    lines = text.split("\n")
    
    table_lines = [l for l in lines if "|" in l]
    print(f"Total extracted table rows: {len(table_lines)}")
    
    if table_lines:
        print("First 10 table rows:")
        for i, l in enumerate(table_lines[:10]):
            print(f"  {i}: {repr(l)}")
    else:
        print("No table rows extracted!")
        print("First 5 lines of text:")
        for i, l in enumerate(lines[:5]):
            print(f"  {i}: {repr(l)}")
