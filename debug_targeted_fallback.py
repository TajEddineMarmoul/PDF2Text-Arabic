import fitz
from pdf2text_arabic._extract import _compute_clip

def test_targeted_fallback(pdf_path, p_num):
    doc = fitz.open(pdf_path)
    page = doc[p_num]
    clip = _compute_clip(page, 8.0, 4.5, 'pct', True, True)
    
    print(f"\n--- Page {p_num+1} ---")
    tabs = page.find_tables(clip=clip, strategy="lines")
    
    final_tables = []
    
    for i, t in enumerate(tabs.tables):
        print(f"  [Lines] Table {i+1}: rows={len(t.rows)}, cols={len(t.header.cells)}, bbox={t.bbox}")
        
        # Define a vertical column clip based on the table's X-coordinates
        x0 = max(clip.x0, t.bbox[0] - 10)
        x1 = min(clip.x1, t.bbox[2] + 10)
        y0 = max(clip.y0, t.bbox[1] - 10)
        col_clip = fitz.Rect(x0, y0, x1, clip.y1)
        
        mixed_tabs = page.find_tables(vertical_strategy="lines", horizontal_strategy="text", clip=col_clip)
        
        best_t = t
        if mixed_tabs.tables:
            # Get the table with the most rows in this column
            for mt in mixed_tabs.tables:
                if len(mt.rows) > len(best_t.rows) + 2:
                    best_t = mt
                    
        if best_t != t:
            print(f"    -> Upgraded to [Mixed]: rows={len(best_t.rows)}, cols={len(best_t.header.cells)}, bbox={best_t.bbox}")
        else:
            print(f"    -> Kept [Lines]")
            
        final_tables.append(best_t)
        
    doc.close()

pdf = 'download/قانون-المالية-2023.pdf'
for p in [16, 23, 24, 57, 115]:
    test_targeted_fallback(pdf, p)
