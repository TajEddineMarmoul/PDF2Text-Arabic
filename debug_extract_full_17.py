import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic._tables import extract_tables

pdf_path = 'download/قانون-المالية-2023.pdf'

doc = fitz.open(pdf_path)
page17 = doc[16]
clip17 = _compute_clip(page17, 8.0, 4.5, 'pct', True, True)

results, bboxes, state = extract_tables(page17, clip=clip17)
for r in results:
    print(r[1])

doc.close()