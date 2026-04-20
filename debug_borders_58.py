import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic._tables import _has_side_borders

doc = fitz.open('download/قانون-المالية-2023.pdf')
page = doc[57]
clip = _compute_clip(page, 8.0, 4.5, 'pct', True, True)

drawings = page.get_drawings()
left_segments = 0
right_segments = 0
w = clip.width
left_zone = (clip.x0, clip.x0 + w * 0.15)
right_zone = (clip.x1 - w * 0.15, clip.x1)

print(f"clip: {clip}")
print(f"left_zone: {left_zone}")
print(f"right_zone: {right_zone}")

for d in drawings:
    r = d["rect"]
    if not (clip.y0 <= r.y0 <= clip.y1):
        continue
    if r.width < 5:
        if left_zone[0] <= r.x0 <= left_zone[1]:
            left_segments += r.height
            print(f"Left segment: {r}, height={r.height}")
        elif right_zone[0] <= r.x0 <= right_zone[1]:
            right_segments += r.height
            print(f"Right segment: {r}, height={r.height}")

print(f"Left segments: {left_segments}")
print(f"Right segments: {right_segments}")
print(f"has_borders: {left_segments > 200 and right_segments > 200}")
doc.close()