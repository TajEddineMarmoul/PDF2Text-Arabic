import fitz
import os
from pdf2text_arabic._extract import extract_page
from pdf2text_arabic.debug import get_debug_pixmap

# Target: naw.pdf, page 58 (index 57)
pdf_path = "download/naw.pdf"
page_index = 57 
output_dir = "output/test_page"

os.makedirs(output_dir, exist_ok=True)

print(f"Testing single page with on_empty='auto': {pdf_path} [Page {page_index + 1}]")

if not os.path.exists(pdf_path):
    print(f"Error: {pdf_path} not found.")
else:
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    
    # 1. Run extraction
    try:
        text, _ = extract_page(page, on_empty="auto")
        
        txt_path = os.path.join(output_dir, f"page_{page_index + 1}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Extracted text saved to {txt_path}")
        
    except Exception as e:
        print(f"Extraction failed: {e}")
    
    # 2. Save debug image
    pix = get_debug_pixmap(page, dpi=120, on_empty="auto")
    img_path = os.path.join(output_dir, f"page_{page_index + 1}.png")
    pix.save(img_path)
    print(f"Debug image saved to {img_path}")
    
    doc.close()
