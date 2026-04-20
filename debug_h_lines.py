import fitz
from pdf2text_arabic._extract import _compute_clip

def check_horizontal_span(pdf_path, p_num):
    doc = fitz.open(pdf_path)
    page = doc[p_num]
    clip = _compute_clip(page, 8.0, 4.5, 'pct', True, True)
    
    drawings = page.get_drawings()
    max_h_width = 0
    for d in drawings:
        r = d["rect"]
        if clip.y0 <= r.y0 <= clip.y1:
            if r.height < 5:  # Horizontal line
                if r.width > max_h_width:
                    max_h_width = r.width
                    
    print(f"Page {p_num+1}: max horizontal line width = {max_h_width}")
    doc.close()

pdf = 'download/قانون-المالية-2023.pdf'
for p in [16, 23, 24, 57, 115]:
    check_horizontal_span(pdf, p)
