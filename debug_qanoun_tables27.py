import fitz
from pdf2text_arabic._extract import _compute_clip

doc = fitz.open(r"download/قانون-المالية-2023.pdf")
for p_num in [20, 21]:
    page = doc[p_num]
    clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)

    tabs = page.find_tables(vertical_strategy="lines", horizontal_strategy="text", clip=page.rect)
    if tabs.tables:
        t = tabs.tables[0]
        print(f"Page {p_num+1} found {len(t.header.cells)} cols using page.rect!")
    else:
        print(f"Page {p_num+1} no tables")
