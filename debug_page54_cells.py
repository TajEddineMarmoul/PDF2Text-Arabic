import fitz

doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[53] # Page 54

tabs = page.find_tables()
if tabs.tables:
    t = tabs.tables[0]
    print(f"Table bbox: {t.bbox}")
    for i, row in enumerate(t.rows):
        print(f"Row {i}:")
        for j, cell in enumerate(row.cells):
            print(f"  Cell {j}: {cell}")
