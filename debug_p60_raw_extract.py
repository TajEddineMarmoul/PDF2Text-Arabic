import fitz
from pdf2text_arabic._extract import _compute_clip

doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[59] # Page 60
clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)

tabs = page.find_tables(clip=clip)
t = tabs.tables[0]
raw_extract = t.extract()

for ri, row in enumerate(raw_extract[:5]):
    print(f"--- Row {ri} ---")
    for ci, cell in enumerate(row):
        print(f"  Col {ci}: {repr(cell)}")
