import fitz

pdf_path = r"download/قانون-المالية-2023.pdf"
doc = fitz.open(pdf_path)
page = doc[21]

drawings = page.get_drawings()
vert_rects = []
for d in drawings:
    for item in d["items"]:
        if item[0] == "re":
            rect = item[1]
            if rect.width < 5.0: # vertical rectangle
                vert_rects.append((rect.x0, rect.y0, rect.y1, rect.height))

vert_rects.sort(key=lambda x: x[0])
print(f"Found {len(vert_rects)} vertical rects")
for x, y1, y2, h in vert_rects:
    print(f"X: {x:.2f}, Y1: {y1:.2f}, Y2: {y2:.2f}, H: {h:.2f}")
