import fitz
from pdf2text_arabic._extract import _compute_clip

doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[59] # Page 60
clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)

tabs = page.find_tables(clip=clip)
t = tabs.tables[0]
print(f"Original table: cols={len(t.header.cells)}, rows={len(t.rows)}")

# Extract column X-coordinates from the original table
v_lines = []
for c in t.header.cells:
    if c:
        v_lines.append(c[0])
v_lines.append(t.bbox[2]) # Add the rightmost edge
v_lines = sorted(list(set(v_lines)))
print(f"Explicit vertical lines: {v_lines}")

col_clip = fitz.Rect(t.bbox[0] - 10, t.bbox[1] - 50, t.bbox[2] + 10, clip.y1)

# Run mixed strategy with explicit vertical lines
mixed_tabs = page.find_tables(
    vertical_strategy="text", 
    horizontal_strategy="text", 
    clip=col_clip,
    vertical_lines=v_lines
)

if mixed_tabs.tables:
    mt = mixed_tabs.tables[0]
    print(f"Fallback table: cols={len(mt.header.cells)}, rows={len(mt.rows)}")
    raw = mt.extract()
    print(f"First row: {raw[0]}")
    print(f"Middle row: {raw[len(raw)//2]}")
else:
    print("No fallback table found.")
