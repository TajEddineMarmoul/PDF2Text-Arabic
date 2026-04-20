import fitz

pdf_path = 'download/قانون-المالية-2023.pdf'
p_num = 16

doc = fitz.open(pdf_path)
page = doc[p_num]

pix = page.get_pixmap(dpi=150)
pix.save("page_17_debug.png")

print("Saved page_17_debug.png")
doc.close()