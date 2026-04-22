import fitz

pdf_path = 'download/naw.pdf'
p_num = 7

doc = fitz.open(pdf_path)
page = doc[p_num]

pix = page.get_pixmap(dpi=150)
pix.save("page_naw_8_debug.jpg")

print("Saved page_naw_8_debug.jpg")
doc.close()