import fitz

pdf_path = 'download/naw.pdf'
doc = fitz.open(pdf_path)
page = doc[7]

rawdict = page.get_text("dict")
for b in rawdict["blocks"]:
    if "lines" in b:
        for l in b["lines"]:
            for s in l["spans"]:
                if "تحددها" in s["text"]:
                    print(f"Span text: '{s['text']}', size: {s['size']}, bbox: {s['bbox']}")
                # Check for standalone numbers
                if s["text"].strip().isdigit():
                     print(f"Digit span: '{s['text']}', size: {s['size']}, bbox: {s['bbox']}")

doc.close()