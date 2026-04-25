import glob
import os
import fitz
from pdf2text_arabic._extract import extract_page
from pdf2text_arabic.debug import get_debug_pixmap

BASE_OUT_DIR = "output/all_pages"
os.makedirs(BASE_OUT_DIR, exist_ok=True)

def process_full_pdf(pdf_path):
    pdf_name = os.path.basename(pdf_path).replace('.pdf', '')
    pdf_out_dir = os.path.join(BASE_OUT_DIR, pdf_name)
    os.makedirs(pdf_out_dir, exist_ok=True)
    
    print(f"\nProcessing Entire PDF: {pdf_name}")
    # Open a fresh document for text extraction
    doc_text = fitz.open(pdf_path)
    # Open a separate document for visual debugging
    doc_vis = fitz.open(pdf_path)
    
    table_state = None
    for p_num in range(len(doc_text)):
        # 1. Extract Text from a CLEAN page
        text, table_state = extract_page(doc_text[p_num], prev_table_state=table_state)
        txt_path = os.path.join(pdf_out_dir, f"page_{p_num+1:03d}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)

        # 2. Generate Visual Debug from the other document copy
        pix = get_debug_pixmap(doc_vis[p_num], dpi=120)
        img_path = os.path.join(pdf_out_dir, f"page_{p_num+1:03d}.png")
        pix.save(img_path)
            
    print(f"  ✓ Saved {len(doc_text)} pages to {pdf_out_dir}/")
    doc_text.close()
    doc_vis.close()

# Process all PDFs
for p in glob.glob("download/*.pdf"):
    process_full_pdf(p)

print("\nAll done!")
