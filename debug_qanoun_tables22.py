import fitz
from pdf2text_arabic._tables import extract_tables
from pdf2text_arabic._extract import _compute_clip

pdf_path = r"download/قانون-المالية-2023.pdf"
doc = fitz.open(pdf_path)

page = doc[20] # Page 21
clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)

results, bboxes, state = extract_tables(page, clip=clip)
if results:
    lines = results[0][1].split("\n")
    for i, line in enumerate(lines):
        if "10" in line or "8" in line or "40" in line or "2,5" in line:
            print(f"Row {i}: {line}")
