import fitz

pdf_path = r"download/قانون-المالية-2023.pdf"
doc = fitz.open(pdf_path)
page = doc[20]

drawings = page.get_drawings()
vert_lines = []
for d in drawings:
    for item in d["items"]:
        if item[0] == "re":
            rect = item[1]
            if rect.width < 5.0: # vertical rectangle
                vert_lines.append((rect.x0, rect.y0, rect.y1, rect.height))

vert_lines.sort(key=lambda x: x[0])
print(f"Found {len(vert_lines)} vertical rects")
if vert_lines:
    print(f"First 3: {vert_lines[:3]}")
    print(f"Last 3: {vert_lines[-3:]}")

