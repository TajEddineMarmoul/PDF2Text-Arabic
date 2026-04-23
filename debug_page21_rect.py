import fitz
doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[20] # Page 21
tabs = page.find_tables(clip=page.rect)
print(f"Found {len(tabs.tables)} tables with page.rect.")
for i, t in enumerate(tabs.tables):
    print(f"Table {i}: bbox={t.bbox}, rows={len(t.rows)}, cols={len(t.header.cells)}")
