import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic._tables import extract_tables, _has_side_borders

doc = fitz.open('download/قانون-المالية-2023.pdf')
page = doc[24]
clip = _compute_clip(page, 8.0, 4.5, 'pct', True, True)

print(f"Has side borders? {_has_side_borders(page, clip)}")

tabs = page.find_tables(clip=clip, strategy="lines")
max_rows = 0
max_cols = 0
if tabs.tables:
    max_rows = max(len(t.rows) for t in tabs.tables)
    max_cols = max(len(t.header.cells) for t in tabs.tables)

print(f"Lines strategy: tables={len(tabs.tables)}, max_rows={max_rows}, max_cols={max_cols}")

text_tabs = page.find_tables(strategy="text", clip=clip)
if text_tabs.tables:
    text_max_rows = max([len(t.rows) for t in text_tabs.tables])
    print(f"Text strategy max rows: {text_max_rows}")

mixed_tabs = page.find_tables(vertical_strategy="lines", horizontal_strategy="text", clip=clip)
if mixed_tabs.tables:
    mixed_max_rows = max([len(t.rows) for t in mixed_tabs.tables])
    print(f"Mixed strategy max rows: {mixed_max_rows}")
    for i, t in enumerate(mixed_tabs.tables):
        print(f"  Mixed Table {i+1}: rows={len(t.rows)}, cols={len(t.header.cells)}, bbox={t.bbox}")

doc.close()