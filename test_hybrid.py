import fitz

def test_hybrid_layout(pdf_path, pages_to_test):
    print(f"\\n{'='*50}\\nTesting Hybrid Layout on: {pdf_path}\\n{'='*50}")
    doc = fitz.open(pdf_path)
    
    for page_num in pages_to_test:
        if page_num >= len(doc): continue
        page = doc[page_num]
        w, h = page.rect.width, page.rect.height
        print(f"\\n--- PAGE {page_num} ---")
        
        # 1. Look for a vertical line in the middle of the page
        paths = page.get_drawings()
        center_line_x = None
        line_y0, line_y1 = 0, 0
        
        for p in paths:
            r = p['rect']
            # Is it a tall vertical line near the center?
            if r.width < 5 and r.height > h * 0.3 and 0.4 * w < r.x0 < 0.6 * w:
                center_line_x = r.x0
                line_y0 = r.y0
                line_y1 = r.y1
                break
                
        if center_line_x:
            print(f"✅ DETECTED: 2-Column layout separated by vertical line at X={center_line_x:.1f}")
        else:
            print(f"✅ DETECTED: Standard 1-Column layout (No separating line found)")
            
        # 2. Find Spanning Tables
        tables = page.find_tables()
        spanning_tables = []
        for t in tables:
            t_width = t.bbox[2] - t.bbox[0]
            if t_width > w * 0.8:
                spanning_tables.append(t.bbox)
                
        if spanning_tables:
            print(f"✅ DETECTED: {len(spanning_tables)} Full-Page Spanning Table(s)")
            
        # 3. Sort Text Blocks
        blocks = page.get_text("blocks")
        text_blocks = [b for b in blocks if b[6] == 0 and b[4].strip()]
        
        if not text_blocks:
            print("⚠️ DETECTED: Page is an Image (No selectable text). Needs LLM OCR.")
            continue
            
        # Sorting Logic
        def sort_key(b):
            bx0, by0, bx1, by1, text, block_no, block_type = b
            
            # If there's a center line, check if block is beside it
            if center_line_x:
                # Is block vertically alongside the line?
                if by1 > line_y0 and by0 < line_y1:
                    # It's inside the columns! Right column goes first (0), Left goes second (1)
                    col = 0 if bx0 > center_line_x else 1
                    return (1, col, by0) # Category 1: Columns
                elif by1 <= line_y0:
                    return (0, 0, by0) # Category 0: Headers (Above the line)
                else:
                    return (2, 0, by0) # Category 2: Footers (Below the line)
                    
            # If no line, just read top to bottom, right to left
            return (0, 0, by0)
            
        text_blocks.sort(key=sort_key)
        
        print("\\nReading Order Extract (First 5 blocks):")
        for b in text_blocks[:5]:
            snippet = b[4].replace('\\n', ' ').strip()
            print(f"  -> {snippet[:80]}...")

    doc.close()

if __name__ == "__main__":
    # Test the 1978 Document (Imposter page 0, Image pages 1 & 2)
    test_hybrid_layout(r"download/قانون المالية 1978-1747912262117.pdf", [0, 1])
    
    # Test the 2023 Document (Has tables on pages 14-15, and middle lines on early pages)
    test_hybrid_layout(r"download/قانون-المالية-2023.pdf", [0, 1, 14, 15])