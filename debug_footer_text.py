import fitz
from pdf2text_arabic._extract import _compute_clip

def debug_footer_text(pdf_path, p_num):
    doc = fitz.open(pdf_path)
    page = doc[p_num]
    clip = _compute_clip(page, 8.0, 4.5, 'pct', True, True)
    
    # Let's get the text of the bottom 40% of the page
    y = clip.y0 + clip.height * 0.6
    below_clip = fitz.Rect(clip.x0, y, clip.x1, clip.y1)
    below_text = page.get_text("text", clip=below_clip).strip()
    
    print(f"\n--- Bottom text of {pdf_path} Page {p_num+1} ---")
    print(below_text)
    doc.close()

debug_footer_text('download/naw.pdf', 7)
debug_footer_text('download/ظهـير شريف رقم 1.06.07 بتنفيذ القانون رقم 80.03 المحدثة-1772789885018.pdf', 6)
