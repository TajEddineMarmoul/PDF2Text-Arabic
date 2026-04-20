import fitz

pdf_path = 'download/قانون-المالية-2023.pdf'
p_num = 24  # Page 25

doc = fitz.open(pdf_path)
page = doc[p_num]

pix = page.get_pixmap(dpi=150)
pix.save("page_25_debug.jpg")

print("Saved page_25_debug.jpg")
doc.close()