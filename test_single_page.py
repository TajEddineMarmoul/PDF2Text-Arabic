import fitz
import os
from pdf2text_arabic._extract import extract_page
from pdf2text_arabic.debug import get_debug_pixmap

# Target: pick the PDF and the 1-based page number you want to test
pdf_path = "download/قانون-المالية-2023.pdf"
page_number = 24  # 1-based
output_dir = "output/test_page"

os.makedirs(output_dir, exist_ok=True)

print(f"Testing single page: {pdf_path} [Page {page_number}]")

if not os.path.exists(pdf_path):
    print(f"Error: {pdf_path} not found.")
else:
    doc_text = fitz.open(pdf_path)
    doc_vis = fitz.open(pdf_path)
    page_index = page_number - 1

    # 1. Extract text on a pristine page instance
    page_text = doc_text.load_page(page_index)
    try:
        text, _ = extract_page(page_text, ocr_strategy="force")
        txt_path = os.path.join(output_dir, f"page_{page_number:03d}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Extracted text saved to {txt_path}")
    except Exception as e:
        print(f"Extraction failed: {e}")

    # 2. Save debug overlay image on a separate page instance
    page_vis = doc_vis.load_page(page_index)
    pix = get_debug_pixmap(page_vis, dpi=120, ocr_strategy="force")
    img_path = os.path.join(output_dir, f"page_{page_number:03d}.png")
    pix.save(img_path)
    print(f"Debug image saved to {img_path}")

    doc_text.close()
    doc_vis.close()
