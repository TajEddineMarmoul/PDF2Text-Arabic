import fitz

pdf_path = r"download/قانون-المالية-2023.pdf"
doc = fitz.open(pdf_path)
page = doc[21]

drawings = page.get_drawings()
vert_lines = []
for d in drawings:
    for item in d["items"]:
        if item[0] == "l":
            p1, p2 = item[1], item[2]
            if abs(p1.x - p2.x) < 1.0: # vertical
                vert_lines.append((p1.x, min(p1.y, p2.y), max(p1.y, p2.y)))

vert_lines.sort(key=lambda x: x[0])
print(f"Found {len(vert_lines)} vertical lines")
for x, y1, y2 in vert_lines:
    print(f"X: {x:.2f}, Y1: {y1:.2f}, Y2: {y2:.2f}, Len: {y2-y1:.2f}")

