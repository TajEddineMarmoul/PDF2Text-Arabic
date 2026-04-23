import fitz
doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[16] # Page 17
drawings = page.get_drawings()
v_lines = []
for d in drawings:
    for item in d["items"]:
        if item[0] == "re":
            r = item[1]
            if r.width < 5.0 and r.height > 10.0:
                v_lines.append((r.x0, min(r.y0, r.y1), max(r.y0, r.y1)))
        elif item[0] == "l":
            p1, p2 = item[1], item[2]
            if abs(p1.x - p2.x) < 2.0 and abs(p1.y - p2.y) > 10.0:
                v_lines.append((p1.x, min(p1.y, p2.y), max(p1.y, p2.y)))

v_lines.sort(key=lambda x: x[1])
print(f"Found {len(v_lines)} vertical lines.")
for x, y0, y1 in v_lines[:20]:
    print(f"X: {x:.2f}, Y: {y0:.2f} -> {y1:.2f}, H: {y1-y0:.2f}")
