import fitz
import os
from pdf2text_arabic.debug import draw_page_layout

# 1. Setup output directory
output_root = "output/visual_audit"
if not os.path.exists(output_root):
    os.makedirs(output_root)

# Monkey-patch display to save images to files
import pdf2text_arabic.debug as debug
original_display = debug.display

def save_visual_debug(pdf_path):
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    pdf_dir = f"{output_root}/{pdf_name}"
    if not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir)
        
    print(f"Processing Visuals for: {pdf_name}")
    doc = fitz.open(pdf_path)
    
    for page_num in range(len(doc)):
        img_path = f"{pdf_dir}/page_{page_num+1:03d}.png"
        
        def mock_display(obj):
            with open(img_path, "wb") as f:
                f.write(obj.data)
        
        debug.display = mock_display
        try:
            draw_page_layout(doc[page_num], dpi=120)
        except Exception as e:
            print(f"  [ERROR] Page {page_num+1}: {e}")
    
    print(f"  ✓ Saved {len(doc)} images to {pdf_dir}")

# Find all PDFs in download/
download_dir = "download"
for file in os.listdir(download_dir):
    if file.lower().endswith(".pdf"):
        save_visual_debug(os.path.join(download_dir, file))

debug.display = original_display
print("\nAll visual audits complete. Check 'output/visual_audit' folder.")
