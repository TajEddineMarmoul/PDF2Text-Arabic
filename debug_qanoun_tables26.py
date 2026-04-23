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

# If I use page.rect, I get 11 columns.
tabs_mixed = page.find_tables(
    vertical_strategy="lines", 
    horizontal_strategy="text", 
    vertical_lines=v_lines,
    snap_tolerance=5,
    clip=page.rect
)

t = tabs_mixed.tables[0]
print(f"Table cols with page.rect: {len(t.header.cells)}")

# What if I use clip but adjust snap_x_tolerance? No, I tried that.
# What if I manually crop the cells AFTER extracting with page.rect?
# If I extract with page.rect, t.bbox will be the whole page table.
# Then I can just ignore rows whose cells fall outside my custom `clip`!

print(f"First row Y: {t.rows[0].bbox}")
print(f"Clip Y: {clip.y0} to {clip.y1}")
