import fitz
import os
import glob
from pdf2text_arabic._extract import extract_page
from pdf2text_arabic.debug import get_debug_pixmap

output_dir = "output/sample_tests"
os.makedirs(output_dir, exist_ok=True)

# List of tuples: (glob_pattern, page_index_to_test, description)
test_cases = [
    ("download/naw.pdf", 57, "Page 58 - Complex layout with standalone scanned image"),
    ("download/خطاب صاحب الجلالة*.pdf", 0, "Page 1 - Khitab with full background image"),
    ("download/قانون-المالية-2023.pdf", 17, "Page 18 - Complex tables, no background images"),
    ("download/- ظهير شريف رقم 1.15.73*.pdf", 0, "Page 1 - Standard legal text")
]

print("Running targeted 'auto' extraction tests...\n")

for pattern, page_idx, desc in test_cases:
    paths = glob.glob(pattern)
    if not paths:
        print(f"[SKIPPED] {desc}: File not found matching {pattern}")
        continue
        
    pdf_path = paths[0]
    filename = os.path.basename(pdf_path)[:20] + "..."
    
    print(f"Testing: {desc}")
    print(f"File: {filename} (Page {page_idx + 1})")
    
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_idx]
        
        text, _ = extract_page(page, on_empty="auto")
        
        # Save text
        safe_name = f"sample_{page_idx + 1}_{os.path.basename(pdf_path)[:15].replace(' ', '_')}"
        txt_path = os.path.join(output_dir, f"{safe_name}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)
            
        # Save debug image
        pix = get_debug_pixmap(page, dpi=120, on_empty="auto")
        img_path = os.path.join(output_dir, f"{safe_name}.png")
        pix.save(img_path)
        
        # Determine if OCR was likely triggered based on the output text 
        # (if text is present but PyMuPDF would have failed, or by checking the debug image visually later)
        # We can also just count chars
        char_count = len(text)
        print(f"  -> Success: Extracted {char_count} chars.")
        print(f"  -> Saved: {txt_path}")
        print(f"  -> Saved: {img_path}\n")
        
        doc.close()
    except Exception as e:
        print(f"  -> FAILED: {e}\n")

print("Finished testing sample pages.")
