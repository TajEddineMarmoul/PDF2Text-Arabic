import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic._tables import extract_tables

doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[53] # Page 54
clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)

print("--- TESTING PAGE 54 (CURRENT LOGIC) ---")
# Current logic uses page.rect inside extract_tables
results, bboxes, state = extract_tables(page, clip=clip)
if results:
    for i, (res, bbox) in enumerate(zip(results, bboxes)):
        print(f"Table {i+1} bbox: {bbox}")
        text = res[1]
        lines = text.split('\n')
        print(f"Rows: {len(lines)}")
        if len(lines) > 50:
            print("ERROR: Detected giant table that likely includes paragraph text!")
            print(f"First line snippet: {repr(lines[0][:100])}")
else:
    print("No tables found.")
