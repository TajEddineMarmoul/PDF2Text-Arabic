import fitz
from pdf2text_arabic._extract import _compute_clip

pdf_path = 'download/ظهـير شريف رقم 1.06.07 بتنفيذ القانون رقم 80.03 المحدثة-1772789885018.pdf'
doc = fitz.open(pdf_path)
page = doc[6] # Page 7
clip = _compute_clip(page, 8.0, 4.5, 'pct', True, True)

print(f"Page 7 Images info:")
image_infos = page.get_image_info()
for i, img in enumerate(image_infos):
    bbox = fitz.Rect(img["bbox"])
    intersection = bbox & clip
    if intersection.is_empty: continue
    print(f"  Image {i}: bbox={bbox}, intersection={intersection}, w={intersection.width:.1f}, h={intersection.height:.1f}")
    
    selectable = page.get_text("text", clip=intersection).strip()
    print(f"    Selectable text inside (len={len(selectable)}): '{selectable}'")

# Check for small text blocks (superscripts)
print("\nChecking selectable text blocks:")
blocks = page.get_text("blocks", clip=clip)
for b in blocks:
    if b[6] == 0:
        text = b[4].strip()
        if len(text) < 10:
            print(f"  Small text block: '{text}' at bbox {b[:4]}")

doc.close()