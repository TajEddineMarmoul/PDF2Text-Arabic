import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic._tables import extract_tables

doc = fitz.open('download/قانون-المالية-2023.pdf')
page = doc[57]
clip = _compute_clip(page, 8.0, 4.5, 'pct', True, True)

print("--- Default find_tables ---")
tabs = page.find_tables(clip=clip)
for i, t in enumerate(tabs.tables):
    print(f"Table {i+1}: rows={len(t.rows)}, cols={len(t.header.cells)}, bbox={t.bbox}")

print("\n--- extract_tables ---")
results, bboxes, state = extract_tables(page, clip=clip)
print(f"Number of formatted tables: {len(results)}")
for r in results:
    lines = r[1].split('\n')
    print(f"Bbox Y-top: {r[0]}")
    for L in lines[:10]:
        print(L)
    print("...")

doc.close()