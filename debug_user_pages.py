import fitz
import os
from pdf2text_arabic._extract import extract_page

doc = fitz.open(r"download/قانون-المالية-2023.pdf")

# We will modify the debug module temporarily to save the image instead of just displaying it
with open("pdf2text_arabic/debug.py", "r", encoding="utf-8") as f:
    debug_code = f.read()

debug_code = debug_code.replace("display(Image(data=pix.tobytes(\"png\")))", "with open(f'page_{page.number + 1}_vis.jpg', 'wb') as f: f.write(pix.tobytes('png'))")

with open("pdf2text_arabic/temp_debug.py", "w", encoding="utf-8") as f:
    f.write(debug_code)

from pdf2text_arabic import temp_debug

for p in [16, 53]:
    print(f"\n--- Processing Page {p+1} ---")
    page = doc[p]
    temp_debug.draw_page_layout(page)
    print(f"Saved visual debug to page_{p+1}_vis.jpg")
    
    text, state = extract_page(page)
    print(f"Extracted Text (first 20 lines):")
    lines = text.split('\n')
    for i, line in enumerate(lines[:20]):
        print(f"{i}: {line}")
    print(f"Total lines extracted: {len(lines)}")

if os.path.exists("pdf2text_arabic/temp_debug.py"):
    os.remove("pdf2text_arabic/temp_debug.py")
