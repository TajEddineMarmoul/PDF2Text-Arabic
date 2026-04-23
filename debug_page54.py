import fitz
from pdf2text_arabic._extract import _compute_clip

doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[53] # Page 54
clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)

print("--- Default find_tables ---")
tabs_default = page.find_tables(clip=clip)
if tabs_default.tables:
    for i, t in enumerate(tabs_default.tables):
        print(f"Table {i+1}: bbox={t.bbox}, rows={len(t.rows)}, cols={len(t.header.cells)}")
else:
    print("No tables found with default strategy.")

print("\n--- Mixed strategy find_tables ---")
tabs_mixed = page.find_tables(vertical_strategy="lines", horizontal_strategy="text", clip=clip)
if tabs_mixed.tables:
    for i, t in enumerate(tabs_mixed.tables):
        print(f"Table {i+1}: bbox={t.bbox}, rows={len(t.rows)}, cols={len(t.header.cells)}")
else:
    print("No tables found with mixed strategy.")
    
print("\n--- Mixed strategy with page.rect ---")
tabs_mixed_rect = page.find_tables(vertical_strategy="lines", horizontal_strategy="text", clip=page.rect)
if tabs_mixed_rect.tables:
    for i, t in enumerate(tabs_mixed_rect.tables):
        print(f"Table {i+1}: bbox={t.bbox}, rows={len(t.rows)}, cols={len(t.header.cells)}")
else:
    print("No tables found with mixed strategy with page.rect.")
