import fitz
import os
from pdf2text_arabic._extract import extract_page

doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[17] # index 17 is page 18

# Modify debug temporarily to save the image
with open("pdf2text_arabic/debug.py", "r", encoding="utf-8") as f:
    debug_code = f.read()

debug_code = debug_code.replace("display(Image(data=pix.tobytes(\"png\")))", "with open(f'page_{page.number + 1}_vis.jpg', 'wb') as f: f.write(pix.tobytes('png'))")

with open("pdf2text_arabic/temp_debug.py", "w", encoding="utf-8") as f:
    f.write(debug_code)

from pdf2text_arabic import temp_debug

print("--- PAGE 18 DEBUG ---")
temp_debug.draw_page_layout(page)
print(f"Saved visual debug to page_18_vis.jpg")

text, state = extract_page(page)
print("\n--- PAGE 18 EXTRACTED TEXT (first 30 lines) ---")
lines = text.split("\n")
for i, line in enumerate(lines[:30]):
    print(f"{i}: {line}")
print(f"Total lines: {len(lines)}")

if os.path.exists("pdf2text_arabic/temp_debug.py"):
    os.remove("pdf2text_arabic/temp_debug.py")
