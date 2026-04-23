import fitz
from pdf2text_arabic._extract import _compute_clip

pdf_path = r"download/قانون-المالية-2023.pdf"
doc = fitz.open(pdf_path)

p_num = 21
print(f"\n--- PAGE {p_num + 1} ---")
page = doc[p_num]
clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)

tabs_mixed = page.find_tables(vertical_strategy="lines", horizontal_strategy="text", clip=clip)
t = tabs_mixed.tables[0]
for ci, cell in enumerate(t.rows[10].cells):
    print(f"Cell {ci} bbox: {cell}")

print("Text near right edge (x > 500) around Y=120..200:")
for block in page.get_text("blocks", clip=clip):
    if block[0] > 500 and 120 < block[1] < 200:
        print(f"  bbox: {block[:4]}, text: {block[4].strip()}")
