import fitz
from pdf2text_arabic._extract import _compute_clip

doc = fitz.open('download/قانون-المالية-2023.pdf')
page = doc[57]
clip = _compute_clip(page, 8.0, 4.5, 'pct', True, True)

drawings = page.get_drawings()
for i, d in enumerate(drawings):
    r = d["rect"]
    if clip.y0 <= r.y0 <= clip.y1:
        if r.width < 5 and r.height > 20:
            print(f"Vertical line: {r}, height={r.height}")
        elif r.height < 5 and r.width > 20:
            print(f"Horizontal line: {r}, width={r.width}")
doc.close()