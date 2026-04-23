import fitz
from pdf2text_arabic._extract import _compute_clip

pdf_path = r"download/قانون-المالية-2023.pdf"
doc = fitz.open(pdf_path)

for p_num in [20, 21]:
    print(f"\n--- PAGE {p_num + 1} ---")
    page = doc[p_num]
    clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)
    
    # default
    t_def = page.find_tables(clip=clip)
    
    # lines_strict / text
    t_mixed_strict = page.find_tables(vertical_strategy="lines_strict", horizontal_strategy="text", clip=clip)
    print("MIXED STRICT:")
    if t_mixed_strict.tables:
        print("BBox:", t_mixed_strict.tables[0].bbox)
        
    # lines / text with explicit vertical lines from default
    v_lines = []
    if t_def.tables:
        bbox = t_def.tables[0].bbox
        v_lines = [(bbox[0], clip.y0), (bbox[0], clip.y1), (bbox[2], clip.y0), (bbox[2], clip.y1)]
        
    t_mixed_added = page.find_tables(vertical_strategy="lines", horizontal_strategy="text", clip=clip, vertical_lines=v_lines)
    print("MIXED ADDED LINES:")
    if t_mixed_added.tables:
        print("BBox:", t_mixed_added.tables[0].bbox)
        ext = t_mixed_added.tables[0].extract()
        print("Row 0 cols:", len(ext[0]))
        print("Row 0:", ext[0])
