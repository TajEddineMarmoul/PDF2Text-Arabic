import fitz
import os
import glob

pdf_dir = "download"
pdfs = glob.glob(os.path.join(pdf_dir, "*.pdf"))

for pdf_path in pdfs:
    try:
        doc = fitz.open(pdf_path)
        if len(doc) > 0:
            page = doc[0]
            w = page.rect.width
            h = page.rect.height
            ratio = w / h
            print(f"{os.path.basename(pdf_path)}: Width={w:.1f}, Height={h:.1f}, Ratio={ratio:.2f}")
        doc.close()
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
