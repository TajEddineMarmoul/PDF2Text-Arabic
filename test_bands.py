import fitz
import os

pdf_path = r'download/قانون المالية 1978-1747912262117.pdf'
doc = fitz.open(pdf_path)
page = doc[0]
w, h = page.rect.width, page.rect.height
blocks = page.get_text("blocks")
text_blocks = [b for b in blocks if b[6] == 0 and b[4].strip()]
mid_x = w / 2

spanning_blocks = []
col_blocks = []

for b in text_blocks:
    x0, y0, x1, y1, text, block_no, block_type = b
    bw = x1 - x0
    center_x = (x0 + x1) / 2
    
    is_spanning = False
    if bw > 0.55 * w:
        is_spanning = True
    elif x0 < mid_x - 0.05 * w and x1 > mid_x + 0.05 * w:
        is_spanning = True
    elif abs(center_x - mid_x) < 0.05 * w:
        is_spanning = True
        
    if is_spanning:
        spanning_blocks.append(b)
    else:
        col_blocks.append(b)

spanning_intervals = [(b[1], b[3], b) for b in spanning_blocks]
spanning_intervals.sort(key=lambda x: x[0])

merged_intervals = []
for interval in spanning_intervals:
    if not merged_intervals:
        merged_intervals.append([interval[0], interval[1], [interval[2]]])
    else:
        last = merged_intervals[-1]
        if interval[0] <= last[1] + 10:
            last[1] = max(last[1], interval[1])
            last[2].append(interval[2])
        else:
            merged_intervals.append([interval[0], interval[1], [interval[2]]])

all_bands = []
current_y = 0
for span in merged_intervals:
    sy0, sy1, sblocks = span
    if sy0 > current_y:
        all_bands.append({'type': 'columns', 'y0': current_y, 'y1': sy0, 'blocks': []})
    all_bands.append({'type': 'spanning', 'y0': sy0, 'y1': sy1, 'blocks': sblocks})
    current_y = sy1

if current_y < h:
    all_bands.append({'type': 'columns', 'y0': current_y, 'y1': h, 'blocks': []})

for b in col_blocks:
    by0, by1 = b[1], b[3]
    b_center_y = (by0 + by1) / 2
    assigned = False
    for band in all_bands:
        if band['type'] == 'columns' and band['y0'] <= b_center_y <= band['y1']:
            band['blocks'].append(b)
            assigned = True
            break
    if not assigned:
        for band in all_bands:
            if band['type'] == 'columns' and band['y0'] - 10 <= b_center_y <= band['y1'] + 10:
                band['blocks'].append(b)
                assigned = True
                break

final_reading_order = []
for band in all_bands:
    if not band['blocks']: continue
    if band['type'] == 'spanning':
        band['blocks'].sort(key=lambda b: b[1])
        for b in band['blocks']:
            final_reading_order.append(('SPANNING', b))
    elif band['type'] == 'columns':
        right_blocks = []
        left_blocks = []
        for b in band['blocks']:
            center_x = (b[0] + b[2]) / 2
            if center_x > mid_x: right_blocks.append(b)
            else: left_blocks.append(b)
        right_blocks.sort(key=lambda b: b[1])
        left_blocks.sort(key=lambda b: b[1])
        for b in right_blocks:
            final_reading_order.append(('RIGHT', b))
        for b in left_blocks:
            final_reading_order.append(('LEFT', b))

print(f"Total blocks: {len(text_blocks)}")
for i, item in enumerate(final_reading_order[:60]):
    assignment, b = item
    print(f"{i:2d}: [{assignment}] {b[4].strip()[:30].replace(chr(10), ' ')}")

doc.close()
