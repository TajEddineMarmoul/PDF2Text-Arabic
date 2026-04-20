import fitz
from pdf2text_arabic._extract import _compute_clip

pdf_path = 'download/قانون-المالية-2023.pdf'

doc = fitz.open(pdf_path)
page17 = doc[16]
clip17 = _compute_clip(page17, 8.0, 4.5, 'pct', True, True)

print("\n--- Strategy: text ---")
tabs = page17.find_tables(clip=clip17, strategy="text")
if tabs.tables:
    t = tabs.tables[0]
    ext = t.extract()
    for ri, row in enumerate(ext):
        print(f"Row {ri}: {row}")

doc.close()