import fitz
from pdf2text_arabic._extract import _compute_clip

pdf_path = 'download/قانون-المالية-2023.pdf'
p_num = 16

doc = fitz.open(pdf_path)
page = doc[p_num]
clip = _compute_clip(page, 8.0, 4.5, 'pct', True, True)

drawings = page.get_drawings()
w = clip.width
left_zone = (clip.x0, clip.x0 + w * 0.15)
right_zone = (clip.x1 - w * 0.15, clip.x1)

left_segments = 0
right_segments = 0

for d in drawings:
    r = d["rect"]
    if not (clip.y0 <= r.y0 <= clip.y1):
        continue
        
    if r.width < 5:
        if left_zone[0] <= r.x0 <= left_zone[1]:
            left_segments += r.height
        elif right_zone[0] <= r.x0 <= right_zone[1]:
            right_segments += r.height

print(f"Left segments total height: {left_segments}")
print(f"Right segments total height: {right_segments}")
print(f"Total drawings: {len(drawings)}")

for i, d in enumerate(drawings[:20]):
    print(f"Drawing {i}: type={d['type']}, rect={d['rect']}, width={d['rect'].width}, height={d['rect'].height}")

doc.close()