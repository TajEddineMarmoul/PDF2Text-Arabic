import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic._tables import extract_tables

doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[57] # Page 58
clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)

print("--- TESTING PAGE 58 (WITH TARGETED FALLBACK) ---")
results, bboxes, state = extract_tables(page, clip=clip)
if results:
    for i, (res, bbox) in enumerate(zip(results, bboxes)):
        print(f"Table {i+1} bbox: {bbox}, Rows: {len(res[1].split(chr(10)))}")
        # Check if it includes "الباب الثالث" (should not)
        if "الباب الثالث" in res[1]:
            print("WARNING: Table contains page header text!")
else:
    print("No tables found.")
