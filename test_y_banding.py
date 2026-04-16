import fitz

def test_y_banding(pdf_path):
    print(f"Testing Y-Banding on: {pdf_path}")
    doc = fitz.open(pdf_path)
    page = doc[0]
    
    # Get all text blocks
    blocks = page.get_text("blocks")
    
    # Filter out images (block_type == 1) and empty blocks
    text_blocks = [b for b in blocks if b[6] == 0 and b[4].strip()]
    
    # --- The Y-Banding Algorithm ---
    # 1. Sort all blocks roughly by their top Y coordinate
    text_blocks.sort(key=lambda b: b[1])
    
    bands = []
    current_band = []
    current_band_bottom = -1
    
    for b in text_blocks:
        x0, y0, x1, y1, text, block_no, block_type = b
        
        # If this block's top (y0) is below the current band's bottom (y1),
        # it means we have moved down to a new row/band!
        # (We use a tiny 5-point overlap tolerance for slight skews)
        if not current_band or y0 > current_band_bottom - 5:
            if current_band:
                bands.append(current_band)
            current_band = [b]
            current_band_bottom = y1
        else:
            # It overlaps vertically with the current band! They are side-by-side.
            current_band.append(b)
            # Expand the band's bottom if this block is taller
            current_band_bottom = max(current_band_bottom, y1)
            
    if current_band:
        bands.append(current_band)
        
    # 2. Sort blocks INSIDE each band Right-to-Left
    print("\\n--- EXTRACTED READING ORDER ---")
    for i, band in enumerate(bands):
        # Sort by X1 (Right edge) descending (highest X first for Arabic)
        band.sort(key=lambda b: b[2], reverse=True)
        
        print(f"\\n[Row {i+1}] - {len(band)} block(s) side-by-side:")
        for b in band:
            # Clean up the text to print nicely
            snippet = b[4].replace('\\n', ' ').strip()
            print(f"  -> {snippet[:60]}...")

    doc.close()

if __name__ == "__main__":
    # Test on the 1978 document
    test_y_banding(r"download/قانون المالية 1978-1747912262117.pdf")
