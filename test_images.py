import fitz

def check_images(pdf_path):
    print(f"Checking images in {pdf_path}")
    doc = fitz.open(pdf_path)
    for i in range(min(5, len(doc))):
        page = doc[i]
        images = page.get_images()
        print(f"  Page {i+1} images: {images}")
    doc.close()

import glob
for p in glob.glob("download/*.pdf"):
    check_images(p)
