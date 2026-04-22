import fitz

pdf_path = 'download/ظهـير شريف رقم 1.06.07 بتنفيذ القانون رقم 80.03 المحدثة-1772789885018.pdf'
doc = fitz.open(pdf_path)
page = doc[6] # Page 7

drawings = page.get_drawings()
small_drawings = [d for d in drawings if d["rect"].width < 20 and d["rect"].height < 20]
print(f"Page 7 has {len(drawings)} total drawings, {len(small_drawings)} small drawings.")
for d in small_drawings:
    print(f"  Small drawing: bbox={d['rect']}, width={d['rect'].width:.1f}, height={d['rect'].height:.1f}")

# Also check rawdict text for superscripts
rawdict = page.get_text("dict")
for b in rawdict["blocks"]:
    if "lines" in b:
        for l in b["lines"]:
            for s in l["spans"]:
                text = s["text"].strip()
                if text.isdigit() and len(text) < 3:
                     print(f"Digit span: '{text}', size: {s['size']}, bbox: {s['bbox']}")

doc.close()