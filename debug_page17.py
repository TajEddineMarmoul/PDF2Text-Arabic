import fitz
from pdf2text_arabic._extract import _compute_clip

pdf_path = 'download/قانون-المالية-2023.pdf'
p_num = 16  # page 17

doc = fitz.open(pdf_path)
page = doc[p_num]
clip = _compute_clip(page, 8.0, 4.5, 'pct', True, True)

print(f"\n--- Default (lines) ---")
tabs = page.find_tables(clip=clip, strategy="lines")
for i, t in enumerate(tabs.tables):
    print(f"Table {i+1}: rows={len(t.rows)}, cols={len(t.header.cells)}, bbox={t.bbox}")

print(f"\n--- Strategy: lines_strict ---")
tabs = page.find_tables(clip=clip, strategy="lines_strict")
for i, t in enumerate(tabs.tables):
    print(f"Table {i+1}: rows={len(t.rows)}, cols={len(t.header.cells)}, bbox={t.bbox}")

print(f"\n--- Strategy: text ---")
tabs = page.find_tables(clip=clip, strategy="text")
for i, t in enumerate(tabs.tables):
    print(f"Table {i+1}: rows={len(t.rows)}, cols={len(t.header.cells)}, bbox={t.bbox}")

doc.close()