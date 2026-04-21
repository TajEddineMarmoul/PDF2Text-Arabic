import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic._tables import extract_tables

doc = fitz.open('download/قانون-المالية-2023.pdf')
p_num = 17 # Page 18
page = doc[p_num]
clip = _compute_clip(page, 8.0, 4.5, 'pct', True, True)

print(f"\n--- Debug Tables: Page {p_num+1} ---")
tabs = page.find_tables(clip=clip, strategy="lines")
print(f"  [Lines] Raw tables found: {len(tabs.tables)}")
for i, t in enumerate(tabs.tables):
    print(f"    Table {i+1}: rows={len(t.rows)}, cols={len(t.header.cells)}, bbox={t.bbox}")

results, bboxes, state = extract_tables(page, clip=clip)
print(f"\nExtracted {len(results)} formatted tables")
if results:
    lines = results[0][1].split('\n')
    for L in lines[:10]:
        print(L)

doc.close()