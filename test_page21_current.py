import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic._tables import extract_tables

doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[20] # Page 21
clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)

print("--- TESTING PAGE 21 (CURRENT LOGIC) ---")
# Current logic uses page.rect inside extract_tables
results, bboxes, state = extract_tables(page, clip=clip)
if results:
    for i, (res, bbox) in enumerate(zip(results, bboxes)):
        print(f"Table {i+1} bbox: {bbox}")
        text = res[1]
        lines = text.split('\n')
        # Check for rates (8, 10, 2.5) which are in far columns
        found_rates = any("10" in l or "2,5" in l or " 8 " in l for l in lines)
        print(f"Found rates (outer columns): {found_rates}")
else:
    print("No tables found.")
