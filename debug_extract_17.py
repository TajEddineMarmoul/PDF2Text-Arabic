import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic._tables import extract_tables

pdf_path = 'download/قانون-المالية-2023.pdf'

doc = fitz.open(pdf_path)
page17 = doc[16]
clip17 = _compute_clip(page17, 8.0, 4.5, 'pct', True, True)

print("Running extract_tables on Page 17 (index 16):")
results, bboxes, state = extract_tables(page17, clip=clip17)
print(f"Number of tables formatted: {len(results)}")
for r in results:
    lines = r[1].split('\n')
    print(f"Table output preview (first 5 lines): {lines[:5]}")
    print(f"Total blocks in this table output: {r[1].count('---') // 2}")

doc.close()