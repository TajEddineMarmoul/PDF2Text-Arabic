import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic._tables import extract_tables

doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[59] # Page 60
clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)

print("Running extract_tables on Page 60:")
tabs = page.find_tables(clip=clip)
print(f"Default tables: {[(t.bbox, len(t.header.cells)) for t in tabs.tables]}")

results, bboxes, state = extract_tables(page, clip=clip)
for i, bbox in enumerate(bboxes):
    print(f"Final extracted table {i} bbox: {bbox}")
    lines = results[i][1].split('\n')
    print(f"Cols in extracted row 0: {len(lines[0].split(' | '))}")
