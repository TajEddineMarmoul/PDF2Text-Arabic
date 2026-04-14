import fitz
import os

pdf_path = r"download/قانون المالية 1978-1747912262117.pdf"
doc = fitz.open(pdf_path)
page = doc[0]

print(f"Page size: {page.rect}")

# Let's check for drawings/lines (like a vertical line separating columns)
paths = page.get_drawings()
for i, p in enumerate(paths[:10]):
    print(f"Drawing {i}: rect={p['rect']}, type={p['type']}")

# Let's check block coordinates
blocks = page.get_text("blocks")
left_blocks = 0
right_blocks = 0
mid_x = page.rect.width / 2

for b in blocks[:15]:
    bx0, by0, bx1, by1, text, block_no, block_type = b
    if block_type != 0: continue
    
    if bx1 < mid_x:
        left_blocks += 1
        print(f"LEFT: x0={bx0:.1f}, x1={bx1:.1f}, text={text.strip()[:20]}")
    elif bx0 > mid_x:
        right_blocks += 1
        print(f"RIGHT: x0={bx0:.1f}, x1={bx1:.1f}, text={text.strip()[:20]}")
    else:
        print(f"SPANNING: x0={bx0:.1f}, x1={bx1:.1f}, text={text.strip()[:20]}")

print(f"Left blocks: {left_blocks}, Right blocks: {right_blocks}")
doc.close()
