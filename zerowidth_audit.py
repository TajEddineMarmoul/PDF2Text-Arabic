import fitz
import glob
from pdf2text_arabic._extract import extract_page

zero_width_chars = set()

for p in glob.glob("download/*.pdf"):
    doc = fitz.open(p)
    for p_num in range(min(5, len(doc))): # just check first 5 pages of each
        page = doc.load_page(p_num)
        rawdict = page.get_text("rawdict")
        for b in rawdict.get("blocks", []):
            for l in b.get("lines", []):
                for s in l.get("spans", []):
                    for c in s.get("chars", []):
                        w = c['bbox'][2] - c['bbox'][0]
                        if w < 1.0 and c['c'].strip() and c['c'] not in "\u200b\u200c\u200d\ufeff\u200e\u200f":
                            zero_width_chars.add(c['c'])
    doc.close()

print("Zero-width visible characters found in corpus:")
print(zero_width_chars)
