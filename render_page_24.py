import fitz

pdf_path = 'download/قانون-المالية-2023.pdf'
p_num = 23

doc = fitz.open(pdf_path)
page = doc[p_num]

pix = page.get_pixmap(dpi=150)
pix.save("page_24_debug.jpg")

print("Saved page_24_debug.jpg")
doc.close()