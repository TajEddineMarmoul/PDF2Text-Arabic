import fitz
import glob
from pdf2text_arabic._extract import extract_page

for p in glob.glob("download/*.pdf"):
    doc = fitz.open(p)
    for p_num in range(len(doc)):
        page = doc.load_page(p_num)
        text, rawdict = extract_page(page)
        if "البرملان" in text:
            print(f"Found in {p}, page {p_num+1}")
            break
    doc.close()
