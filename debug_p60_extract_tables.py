import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic._tables import extract_tables

doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[59] # Page 60
clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)

results, bboxes, state = extract_tables(page, clip=clip)
for i, (y, text) in enumerate(results):
    print(f"\n--- Table {i} ---")
    lines = text.split('\n')
    for j, l in enumerate(lines[:10]):
        print(f"Row {j}: {l}")
