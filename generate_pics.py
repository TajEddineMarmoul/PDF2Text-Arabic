import fitz
import os

with open("pdf2text_arabic/debug.py", "r", encoding="utf-8") as f:
    debug_code = f.read()

debug_code = debug_code.replace("display(Image(data=pix.tobytes(\"png\")))", "with open(f'page_{page.number + 1}_debug.png', 'wb') as f: f.write(pix.tobytes('png'))")

with open("pdf2text_arabic/temp_debug.py", "w", encoding="utf-8") as f:
    f.write(debug_code)

from pdf2text_arabic import temp_debug
doc = fitz.open(r"download/قانون-المالية-2023.pdf")

print("Generating page 21...")
temp_debug.draw_page_layout(doc[20])
print("Generating page 22...")
temp_debug.draw_page_layout(doc[21])
print("Done!")

os.remove("pdf2text_arabic/temp_debug.py")
