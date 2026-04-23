import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic._tables import extract_tables

doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[16] # Page 17
clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)

print("--- TESTING PAGE 17 (WITH FIX) ---")
results, bboxes, state = extract_tables(page, clip=clip)
if results:
    for i, (res, bbox) in enumerate(zip(results, bboxes)):
        print(f"Table {i+1} bbox: {bbox}")
        lines = res[1].split('\n')
        print(f"Rows: {len(lines)}")
else:
    print("No tables found.")
