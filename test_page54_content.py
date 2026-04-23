import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic._tables import extract_tables

doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[53] # Page 54
clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)

print("--- CONTENT OF PAGE 54 (CURRENT LOGIC) ---")
results, bboxes, state = extract_tables(page, clip=clip)
if results:
    for i, (res, bbox) in enumerate(zip(results, bboxes)):
        print(f"Table {i+1} rows:")
        lines = res[1].split('\n')
        for j, line in enumerate(lines[:10]):
            print(f"Row {j}: {line}")
else:
    print("No tables found.")
