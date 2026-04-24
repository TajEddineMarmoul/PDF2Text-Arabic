import fitz
from pdf2text_arabic._extract import _compute_clip

doc = fitz.open(r"download/قانون-المالية-2023.pdf")

def test_fallback(p_num):
    page = doc[p_num]
    clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)
    
    tabs = page.find_tables(clip=clip)
    if not tabs.tables:
        print(f"Page {p_num+1}: No initial tables")
        return
        
    t = tabs.tables[0]
    print(f"Page {p_num+1} Initial: cols={len(t.header.cells)}, rows={len(t.rows)}")
    
    col_clip = fitz.Rect(t.bbox[0] - 10, t.bbox[1] - 50, t.bbox[2] + 10, clip.y1)
    
    # Try with default strategy on expanded clip
    tabs_default = page.find_tables(clip=col_clip)
    if tabs_default.tables:
        mt = tabs_default.tables[0]
        print(f"  Fallback (Default): cols={len(mt.header.cells)}, rows={len(mt.rows)}")
    else:
        print("  Fallback (Default): None")
        
    # Try with text strategy
    tabs_text = page.find_tables(clip=col_clip, vertical_strategy="text", horizontal_strategy="text")
    if tabs_text.tables:
        mt = tabs_text.tables[0]
        print(f"  Fallback (Text): cols={len(mt.header.cells)}, rows={len(mt.rows)}")
    else:
        print("  Fallback (Text): None")

test_fallback(59) # Page 60
test_fallback(16) # Page 17
