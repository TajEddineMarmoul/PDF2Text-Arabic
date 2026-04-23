import fitz
import sys
from pdf2text_arabic._tables import extract_tables
from pdf2text_arabic._extract import _compute_clip

pdf_path = r"download/قانون-المالية-2023.pdf"
doc = fitz.open(pdf_path)

for p_num in [20, 21]: # pages 21 and 22
    print(f"\n--- PAGE {p_num + 1} ---")
    page = doc[p_num]
    clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)
    
    # Raw PyMuPDF find_tables
    tabs = page.find_tables(clip=clip)
    print(f"Default strategy found {len(tabs.tables)} tables.")
    for i, t in enumerate(tabs.tables):
        print(f"  Table {i+1}: {len(t.rows)} rows, {len(t.header.cells)} cols. BBox: {t.bbox}")
        if t.rows:
            print(f"    First row cells: {len(t.rows[0].cells)}")
            # Try to print some cell bboxes
            cells = t.rows[0].cells
            print(f"    First cell: {cells[0]}")
            print(f"    Last cell: {cells[-1]}")

    # Our extract_tables wrapper
    results, bboxes, state = extract_tables(page, clip=clip)
    print(f"\nOur extract_tables returned {len(results)} tables.")
    for res, bbox in zip(results, bboxes):
        print(f"  BBox: {bbox}")
        lines = res[1].split("\n")
        print(f"  Rows: {len(lines)}")
        if lines:
            cols = lines[0].split(" | ")
            print(f"  Cols in first row: {len(cols)}")
            print(f"  First row: {lines[0]}")
