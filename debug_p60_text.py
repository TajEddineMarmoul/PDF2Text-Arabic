import fitz
doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[59] # Page 60

print("Text blocks containing 'الفصل' or 'تقديرات':")
for b in page.get_text("blocks"):
    if "الفصل" in b[4] or "تقديرات" in b[4]:
        print(f"  BBox: {b[:4]}, Text: {repr(b[4].strip())}")
