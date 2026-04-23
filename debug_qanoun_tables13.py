import fitz
from pdf2text_arabic._extract import _compute_clip

pdf_path = r"download/قانون-المالية-2023.pdf"
doc = fitz.open(pdf_path)

for p_num in [20, 21]:
    print(f"\n--- PAGE {p_num + 1} ---")
    page = doc[p_num]
    clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)
    
    t_def = page.find_tables(clip=clip)
    
    if t_def.tables:
        bbox = t_def.tables[0].bbox
        print(f"Drawing lines at X={bbox[0]} and X={bbox[2]}")
        # Draw explicit lines
        page.draw_line(fitz.Point(bbox[0], clip.y0), fitz.Point(bbox[0], clip.y1), color=(0,0,0), width=0.5)
        page.draw_line(fitz.Point(bbox[2], clip.y0), fitz.Point(bbox[2], clip.y1), color=(0,0,0), width=0.5)
        
    tabs_mixed = page.find_tables(vertical_strategy="lines", horizontal_strategy="text", clip=clip)
    if tabs_mixed.tables:
        print(f"MIXED with drawn lines: cols={len(tabs_mixed.tables[0].header.cells)}")
        ext = tabs_mixed.tables[0].extract()
        print(f"Row 10: {ext[10] if len(ext) > 10 else ''}")
    else:
        print("MIXED with drawn lines: No tables found.")
