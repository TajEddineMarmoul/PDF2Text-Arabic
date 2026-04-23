import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic._tables import extract_tables

doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[57] # Page 58
clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)

print("--- PAGE 58 TABLE 1 CONTENT ---")
results, bboxes, state = extract_tables(page, clip=clip)
if results:
    text = results[0][1]
    print(text)
else:
    print("No tables found.")
