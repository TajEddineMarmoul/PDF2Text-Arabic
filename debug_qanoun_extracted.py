import fitz
from pdf2text_arabic._extract import extract_page

doc = fitz.open(r"download/قانون-المالية-2023.pdf")
text, state = extract_page(doc[20])
print("--- PAGE 21 TEXT ---")
print("\n".join(text.split("\n")[:20]))

text, state = extract_page(doc[21])
print("\n--- PAGE 22 TEXT ---")
print("\n".join(text.split("\n")[:20]))
