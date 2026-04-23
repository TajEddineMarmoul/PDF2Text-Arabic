import fitz

doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[20]

drawings = page.get_drawings()
x_coords = set()
for d in drawings:
    for item in d["items"]:
        if item[0] == "re" and item[1].width < 5.0:
            x_coords.add(round(item[1].x0, 2))
        elif item[0] == "l" and abs(item[1].x - item[2].x) < 1.0:
            x_coords.add(round(item[1].x, 2))

v_lines = sorted(list(x_coords))
print(f"Found explicit vertical lines: {v_lines}")

tabs = page.find_tables(
    vertical_strategy="lines", 
    horizontal_strategy="text", 
    vertical_lines=v_lines,
    snap_tolerance=5,
    clip=page.rect
)

if tabs.tables:
    t = tabs.tables[0]
    print(f"Table found with {len(t.header.cells)} columns!")
    ext = t.extract()
    print("Row 10:", ext[10] if len(ext)>10 else "")
