import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic._tables import _has_side_borders

def analyze_page(pdf_path, p_num):
    doc = fitz.open(pdf_path)
    page = doc[p_num]
    clip = _compute_clip(page, 8.0, 4.5, 'pct', True, True)
    
    tabs = page.find_tables(clip=clip, strategy="lines")
    
    broken_header = False
    for t in tabs.tables:
        w = t.bbox[2] - t.bbox[0]
        # Condition: less than 5 rows, >=4 columns, width is at least 60% of clip width
        if len(t.rows) < 5 and len(t.header.cells) >= 4 and w > clip.width * 0.6:
            broken_header = True
            break
            
    has_borders = _has_side_borders(page, clip)
    
    print(f"Page {p_num+1}: broken_header={broken_header}, has_borders={has_borders}")
    doc.close()

pdf = 'download/قانون-المالية-2023.pdf'
for p in [16, 23, 24, 115]:
    analyze_page(pdf, p)
