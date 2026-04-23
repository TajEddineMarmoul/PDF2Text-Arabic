import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic._footer import detect_footer_y, _collect_superscript_tips, _get_body_size

def debug_footer(pdf_path, p_num):
    doc = fitz.open(pdf_path)
    page = doc[p_num]
    clip = _compute_clip(page, 8.0, 4.5, 'pct', True, True)
    
    raw_data = page.get_text("rawdict", clip=clip)
    body_size = _get_body_size(raw_data)
    tips = _collect_superscript_tips(page, clip, body_size)
    print(f"File: {pdf_path}, Page: {p_num+1}")
    print(f"  Body size: {body_size:.1f}")
    print(f"  Tips found: {tips}")
    
    footer_y, guaranteed = detect_footer_y(page, clip)
    print(f"  Footer Y: {footer_y}")
    
    doc.close()

debug_footer('download/naw.pdf', 7)
debug_footer('download/ظهـير شريف رقم 1.06.07 بتنفيذ القانون رقم 80.03 المحدثة-1772789885018.pdf', 6)
