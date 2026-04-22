import fitz
from pdf2text_arabic._extract import _compute_clip

pdf_path = 'download/naw.pdf'
doc = fitz.open(pdf_path)
page = doc[7] # Page 8
clip = _compute_clip(page, 8.0, 4.5, 'pct', True, True)

print(f"Page 8 Images info:")
image_infos = page.get_image_info()
for i, img in enumerate(image_infos):
    bbox = fitz.Rect(img["bbox"])
    intersection = bbox & clip
    if intersection.is_empty: continue
    print(f"  Image {i}: bbox={bbox}, intersection={intersection}, w={intersection.width:.1f}, h={intersection.height:.1f}")
    
    # Check if there's selectable text on top of it
    selectable = page.get_text("text", clip=intersection).strip()
    print(f"    Selectable text inside: '{selectable}'")

print("\nChecking selectable text blocks near possible reference markers:")
blocks = page.get_text("blocks", clip=clip)
for b in blocks:
    if b[6] == 0: # text
        text = b[4].strip()
        if len(text) < 10: # likely a small marker or reference
            print(f"  Small text block: '{text}' at bbox {b[:4]}")

doc.close()