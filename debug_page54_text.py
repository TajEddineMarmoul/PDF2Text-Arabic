import fitz
doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[53] # Page 54
for b in page.get_text("blocks"):
    if "يتضمن هذا" in b[4]:
        print(f"Text: {b[4][:50]}... bbox: {b[:4]}")
