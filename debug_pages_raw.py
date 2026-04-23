import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic.debug import draw_page_layout
from pdf2text_arabic._tables import extract_tables

doc = fitz.open(r"download/قانون-المالية-2023.pdf")

def check_pages():
    for p_num in [16, 53, 57]:
        page = doc[p_num]
        clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)

        print(f"\n--- PAGE {p_num+1} RAW PYMUPDF WITH CLIP ---")
        tabs = page.find_tables(clip=clip)
        if tabs.tables:
            for i, t in enumerate(tabs.tables):
                print(f"Table {i+1}: bbox={t.bbox}, rows={len(t.rows)}, cols={len(t.header.cells)}")
        else:
            print("No tables found.")

check_pages()
