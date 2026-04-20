import fitz
from pdf2text_arabic._extract import _compute_clip

pdf_path = 'download/قانون-المالية-2023.pdf'

doc = fitz.open(pdf_path)

print("Page 16 (index 15):")
page16 = doc[15]
clip16 = _compute_clip(page16, 8.0, 4.5, 'pct', True, True)
tabs16 = page16.find_tables(clip=clip16)
for i, t in enumerate(tabs16.tables):
    print(f"  Table {i+1}: rows={len(t.rows)}, cols={len(t.header.cells)}, bbox={t.bbox}")

print("\nPage 17 (index 16):")
page17 = doc[16]
clip17 = _compute_clip(page17, 8.0, 4.5, 'pct', True, True)
tabs17 = page17.find_tables(clip=clip17)
for i, t in enumerate(tabs17.tables):
    print(f"  Table {i+1}: rows={len(t.rows)}, cols={len(t.header.cells)}, bbox={t.bbox}")

doc.close()