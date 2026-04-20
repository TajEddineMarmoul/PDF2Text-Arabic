import fitz
import sys
from pdf2text_arabic._extract import _compute_clip

def test_strategy(pdf_path, p_num):
    doc = fitz.open(pdf_path)
    page = doc[p_num]
    clip = _compute_clip(page, 8.0, 4.5, 'pct', True, True)
    
    print(f"\n--- Debug Tables: {pdf_path} Page {p_num+1} ---")
    
    tabs1 = page.find_tables(clip=clip, strategy="lines")
    t1_valid = [t for t in tabs1.tables if len(t.rows) >= 2 and len(t.header.cells) > 2]
    print(f"  [lines] valid tables: {len(t1_valid)}")
    for i, t in enumerate(t1_valid):
        print(f"    Table {i+1}: rows={len(t.rows)}, cols={len(t.header.cells)}")

    tabs2 = page.find_tables(clip=clip, strategy="text")
    t2_valid = [t for t in tabs2.tables if len(t.rows) >= 2 and len(t.header.cells) > 2]
    print(f"  [text] valid tables: {len(t2_valid)}")
    for i, t in enumerate(t2_valid):
        print(f"    Table {i+1}: rows={len(t.rows)}, cols={len(t.header.cells)}")

    tabs3 = page.find_tables(clip=clip, vertical_strategy="lines", horizontal_strategy="text")
    t3_valid = [t for t in tabs3.tables if len(t.rows) >= 2 and len(t.header.cells) > 2]
    print(f"  [mixed] valid tables: {len(t3_valid)}")
    for i, t in enumerate(t3_valid):
        print(f"    Table {i+1}: rows={len(t.rows)}, cols={len(t.header.cells)}")

    doc.close()

test_strategy('download/قانون-المالية-2023.pdf', 16) # Page 17
test_strategy('download/قانون-المالية-2023.pdf', 115) # Page 116
