import fitz
doc = fitz.open('download/قانون-المالية-2023.pdf')
page = doc[16]
tabs = page.find_tables(vertical_strategy="lines", horizontal_strategy="text")
t = tabs.tables[0]
ext = t.extract()
for i in range(10):
    print(f"Row {i}: {ext[i]}")
doc.close()