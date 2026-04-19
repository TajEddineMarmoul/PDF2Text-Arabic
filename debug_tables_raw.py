import fitz
from pdf2text_arabic._extract import _compute_clip

def debug_find_tables(pdf_path, p_num):
    doc = fitz.open(pdf_path)
    page = doc[p_num]
    clip = _compute_clip(page, 8.0, 4.5, 'pct', True, True)
    
    print(f"\n--- Debug Tables: {pdf_path} Page {p_num+1} ---")
    tabs = page.find_tables(clip=clip)
    print(f"  Raw tables found: {len(tabs.tables)}")
    for i, t in enumerate(tabs.tables):
        print(f"    Table {i+1}: rows={len(t.rows)}, cols={len(t.header.cells)}, bbox={t.bbox}")
        
    doc.close()

pdf = 'download/قانون-المالية-2023.pdf'
# Pages 9, 10, 11, 15, 17, 18
for p in [8, 9, 10, 14, 16, 17]:
    debug_find_tables(pdf, p)
