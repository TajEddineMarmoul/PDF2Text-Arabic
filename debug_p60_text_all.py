import fitz
doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[59] # Page 60

for b in page.get_text("blocks"):
    if b[1] > 170 and b[1] < 220:
        print(f"BBox: {b[:4]}, Text: {repr(b[4].strip())}")
