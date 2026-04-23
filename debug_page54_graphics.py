import fitz
doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[53] # Page 54

drawings = page.get_drawings()
h_lines = []
v_lines = []

for d in drawings:
    for item in d["items"]:
        if item[0] == "re":
            r = item[1]
            if r.width < 5.0: v_lines.append((r.x0, min(r.y0, r.y1), max(r.y0, r.y1)))
            elif r.height < 5.0: h_lines.append((min(r.x0, r.x1), max(r.x0, r.x1), r.y0))
        elif item[0] == "l":
            p1, p2 = item[1], item[2]
            if abs(p1.x - p2.x) < 2.0: v_lines.append((p1.x, min(p1.y, p2.y), max(p1.y, p2.y)))
            elif abs(p1.y - p2.y) < 2.0: h_lines.append((min(p1.x, p2.x), max(p1.x, p2.x), p1.y))

print(f"H lines: {len(h_lines)}, V lines: {len(v_lines)}")
for y in sorted([y for x0,x1,y in h_lines if y > 400]):
    print(f"H line at Y={y:.2f}")
for x in sorted([x for x,y0,y1 in v_lines if y1 > 400]):
    print(f"V line at X={x:.2f}")

tabs = page.find_tables(vertical_strategy="lines", horizontal_strategy="lines")
if tabs.tables:
    for i, t in enumerate(tabs.tables):
        print(f"Lines strategy: Table {i} bbox={t.bbox}")
