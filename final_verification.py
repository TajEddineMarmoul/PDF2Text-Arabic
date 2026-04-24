import fitz
import os
from pdf2text_arabic.debug import draw_page_layout
from pdf2text_arabic._extract import extract_page

# 1. Setup output directory
output_dir = "output/debug_final"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def verify_and_save(pdf_path, page_num, name):
    print(f"\n--- Processing {name} (Page {page_num+1}) ---")
    doc = fitz.open(pdf_path)
    page = doc[page_num]

    # Monkey-patch display to save the visual debug to a file
    import pdf2text_arabic.debug as debug
    original_display = debug.display
    img_path = f"{output_dir}/{name}_debug.png"
    def mock_display(obj):
        with open(img_path, "wb") as f:
            f.write(obj.data)
    debug.display = mock_display

    try:
        # Generate the visual debug (Maroon boxes for reference tips)
        draw_page_layout(page, dpi=200)
        print(f"  [SUCCESS] Visual debug saved to: {img_path}")
        
        # Extract the actual text
        text, _ = extract_page(page)
        
        # Check for specific numbers we were missing
        if name == "naw_p149":
            found = "237" in text
            snippet = [l for l in text.split('\n') if "237" in l]
        else:
            found = "1" in text
            snippet = [l for l in text.split('\n') if "11 نوفمبر" in l]
            
        status = "FOUND" if found else "MISSING"
        print(f"  [TEXT CHECK] Footnote marker: {status}")
        if snippet:
            print(f"  [SNIPPET] {repr(snippet[0])}")
            
    finally:
        debug.display = original_display

# Run verification on the two problematic pages
verify_and_save("download/naw.pdf", 148, "naw_p149")

pdf2 = "download/-ظهير شريف رقم 1.14.44 بروتوكول الاتفاقية الدولية لسلامة الأرواح-1748340514821.pdf"
verify_and_save(pdf2, 1, "dahiir_p002")

print("\nVerification Complete. Please check the 'output/debug_final' folder for images.")
