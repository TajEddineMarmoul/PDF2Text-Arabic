import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic._tables import extract_tables

doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[53] # Page 54
clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)

entries, bboxes, state = extract_tables(page, clip=clip)
print(f"Found {len(entries)} tables.")
for e in entries:
    text = e[1]
    lines = text.split("\n")
    print(f"Table has {len(lines)} rows.")
    for i, l in enumerate(lines[:5]):
        print(f"  {i}: {l}")
