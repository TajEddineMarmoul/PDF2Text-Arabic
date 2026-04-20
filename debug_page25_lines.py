import fitz
doc = fitz.open('download/قانون-المالية-2023.pdf')
page = doc[24]
tabs = page.find_tables(strategy="lines")
for t in tabs.tables:
    print(f"rows={len(t.rows)}, cols={len(t.header.cells)}, bbox={t.bbox}")
doc.close()