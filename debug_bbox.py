import fitz
doc = fitz.open('download/قانون-المالية-2023.pdf')
page = doc[23]
tabs = page.find_tables(strategy="lines")
print("--- Lines Strategy ---")
for t in tabs.tables:
    print(f"bbox: {t.bbox}, rows={len(t.rows)}, cols={len(t.header.cells)}")

print("\n--- Mixed Strategy ---")
tabs2 = page.find_tables(vertical_strategy="lines", horizontal_strategy="text")
for t in tabs2.tables:
    print(f"bbox: {t.bbox}, rows={len(t.rows)}, cols={len(t.header.cells)}")

print("\n--- Text Strategy ---")
tabs3 = page.find_tables(strategy="text")
for t in tabs3.tables:
    print(f"bbox: {t.bbox}, rows={len(t.rows)}, cols={len(t.header.cells)}")
doc.close()