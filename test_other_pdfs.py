import fitz
import os
import numpy as np

def test_smart_banding(pdf_path, page_num=0):
    print(f"\n{'='*50}\nTesting Smart Banding on: {os.path.basename(pdf_path)} (Page {page_num})\n{'='*50}")
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return
        
    doc = fitz.open(pdf_path)
    if page_num >= len(doc):
        print("Page out of range.")
        return
        
    page = doc[page_num]
    w, h = page.rect.width, page.rect.height
    blocks = page.get_text("blocks")
    text_blocks = [b for b in blocks if b[6] == 0 and b[4].strip()]
    
    if not text_blocks:
        print("⚠️ DETECTED: Page is an Image (No selectable text).")
        doc.close()
        return

    # 1. Find the Gutter
    x_density = np.zeros(int(w) + 1)
    for b in text_blocks:
        x0, y0, x1, y1 = b[:4]
        if (x1 - x0) > (w * 0.6): continue
        x_density[int(max(0, x0)):int(min(w, x1))] += 1

    search_start = int(w * 0.3)
    search_end = int(w * 0.7)
    middle_density = x_density[search_start:search_end]

    best_gap_start = 0
    best_gap_len = 0
    current_gap_start = -1

    for i, val in enumerate(middle_density):
        if val == 0:
            if current_gap_start == -1: current_gap_start = i
        else:
            if current_gap_start != -1:
                gap_len = i - current_gap_start
                if gap_len > best_gap_len:
                    best_gap_len = gap_len
                    best_gap_start = current_gap_start
                current_gap_start = -1
    if current_gap_start != -1 and (len(middle_density) - current_gap_start) > best_gap_len:
        best_gap_start = current_gap_start
        best_gap_len = len(middle_density) - current_gap_start

    if best_gap_len >= 10:
        mid_x = search_start + best_gap_start + (best_gap_len / 2)
        print(f"✅ Gutter found at X={mid_x:.1f} (width={best_gap_len})")
    else:
        mid_x = w / 2
        print(f"ℹ️ No clear gutter found. Using center X={mid_x:.1f}")

    spanning_blocks = []
    col_blocks = []

    for b in text_blocks:
        x0, y0, x1, y1 = b[:4]
        bw = x1 - x0
        center_x = (x0 + x1) / 2
        
        is_spanning = False
        if bw > 0.55 * w:
            is_spanning = True
        elif x0 < mid_x - 10 and x1 > mid_x + 10 and bw > 0.15 * w:
            is_spanning = True
        elif abs(center_x - mid_x) < 0.05 * w and bw > 0.15 * w:
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

    print(f"Total Blocks Processed: {len(text_blocks)}")
    
    # Group by assignment type to show the flow
    current_mode = None
    count = 0
    for assignment, b in final_reading_order:
        if assignment != current_mode:
            print(f"\n--- SWITCHING TO {assignment} MODE ---")
            current_mode = assignment
            count = 0
        
        count += 1
        if count <= 3: # Print first 3 of each section to avoid spam
            snippet = b[4].replace('\n', ' ').strip()
            print(f"  -> {snippet[:60]}")
        elif count == 4:
            print(f"  -> [... and more {assignment} blocks ...]")

    doc.close()

if __name__ == "__main__":
    pdf_dir = "download"
    import glob
    pdfs = glob.glob(os.path.join(pdf_dir, "*.pdf"))
    
    # Let's test a few different PDFs
    for pdf in pdfs[:3]: # Test the first 3 PDFs
        test_smart_banding(pdf, page_num=0) # Test page 1
        
    # Also test the 2023 document on a normal text page (e.g. page 6)
    test_smart_banding(r"download/قانون-المالية-2023.pdf", page_num=6)
