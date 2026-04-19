import fitz

def check_image_hashes(pdf_path):
    print(f"Checking {pdf_path}")
    doc = fitz.open(pdf_path)
    for i in range(min(3, len(doc))):
        page = doc[i]
        try:
            infos = page.get_image_info(hashes=True)
            for info in infos:
                print(f"  Page {i} img bbox: {info['bbox']} digest: {info.get('digest')}")
        except Exception as e:
            print(f"  Error: {e}")
    doc.close()

import glob
for p in glob.glob("download/*.pdf")[:2]:
    check_image_hashes(p)
