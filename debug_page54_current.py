import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic.debug import draw_page_layout
from pdf2text_arabic._tables import extract_tables

doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[53] # Page 54
clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)

print("--- RAW PYMUPDF ---")
tabs = page.find_tables(clip=clip)
if tabs.tables:
    for i, t in enumerate(tabs.tables):
        print(f"Table {i+1}: bbox={t.bbox}, rows={len(t.rows)}, cols={len(t.header.cells)}")
else:
    print("No tables found with default strategy.")

print("\n--- OUR EXTRACT_TABLES ---")
entries, bboxes, state = extract_tables(page, clip=clip)
print(f"Found {len(entries)} tables.")
for bbox, text in zip(bboxes, entries):
    print(f"Table bbox: {bbox}, rows: {len(text[1].split(chr(10)))}")
