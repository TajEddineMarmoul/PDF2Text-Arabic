import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic._tables import extract_tables

doc = fitz.open('download/قانون-المالية-2023.pdf')
p_num = 57 # Page 58
page = doc[p_num]
clip = _compute_clip(page, 8.0, 4.5, 'pct', True, True)

results, bboxes, state = extract_tables(page, clip=clip)
print(f"Extracted {len(results)} tables from Page 58")
for r in results:
    print(f"\n--- Table Y={r[0]:.1f} ---")
    print(r[1])

doc.close()