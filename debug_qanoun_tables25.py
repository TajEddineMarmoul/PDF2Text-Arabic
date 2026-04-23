import fitz
from pdf2text_arabic._extract import _compute_clip

doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[20]
clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)

drawings = page.get_drawings()
x_coords = set()
for d in drawings:
    for item in d["items"]:
        if item[0] == "re" and item[1].width < 5.0:
            x_coords.add(round(item[1].x0, 2))
        elif item[0] == "l" and abs(item[1].x - item[2].x) < 1.0:
            x_coords.add(round(item[1].x, 2))

v_lines = sorted(list(x_coords))

tabs_mixed = page.find_tables(
    vertical_strategy="lines", 
    horizontal_strategy="text", 
    vertical_lines=v_lines,
    snap_tolerance=5,
    clip=clip
)

t = tabs_mixed.tables[0]
print(f"Table cols: {len(t.header.cells)}")
for i, row in enumerate(t.extract()[:15]):
    print(f"Row {i}: {row}")
