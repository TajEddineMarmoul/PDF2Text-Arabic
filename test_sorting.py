import fitz
import os

pdf_path = r"download/قانون المالية 1978-1747912262117.pdf"
doc = fitz.open(pdf_path)
page = doc[0]

blocks = page.get_text("blocks")

mid_x = page.rect.width / 2
left_count = 0
right_count = 0
span_count = 0

pieces = []

for b in blocks:
    x0, y0, x1, y1, text, block_no, block_type = b
    if block_type != 0: continue
    
    width = x1 - x0
    pieces.append((y0, x0, x1, text.strip()))

    if width > page.rect.width * 0.6:
        span_count += 1
    elif x1 < mid_x + 20:
        left_count += 1
    elif x0 > mid_x - 20:
        right_count += 1

is_two_column = (left_count > 2 and right_count > 2 and span_count < max(left_count, right_count))
print(f"Left: {left_count}, Right: {right_count}, Spanning: {span_count}, 2-Col: {is_two_column}")

if is_two_column:
    def sort_key(p):
        y, x0, x1, text = p
        # If it's in the top 20% of the page, it's a header, should be first
        if y < page.rect.height * 0.2 and (x1 - x0 > page.rect.width * 0.4):
            return (0, y)
        
        if x0 > mid_x - 20:
            col = 1 # Right column
        else:
            col = 2 # Left column
        return (col, y)
    
    pieces.sort(key=sort_key)
else:
    pieces.sort(key=lambda p: p[0])

print("\n--- Sorted Output ---")
for p in pieces[:15]:
    y, x0, x1, text = p
    print(f"Y={y:.1f}, X0={x0:.1f}, X1={x1:.1f} | {text[:30]}")

doc.close()
