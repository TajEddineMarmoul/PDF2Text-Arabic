import fitz
from pdf2text_arabic._extract import extract_page

doc = fitz.open(r"download/قانون-المالية-2023.pdf")

for p in [20, 21, 57]:
    print(f"\n--- PAGE {p+1} ---")
    text, state = extract_page(doc[p])
    lines = text.split("\n")
    print(f"Total lines: {len(lines)}")
    # Print the lines containing specific values that were previously broken
    for i, line in enumerate(lines):
        if "10" in line or "8" in line or "40" in line or "2,5" in line or "نفقات الإستغلال" in line:
            print(f"{i}: {line}")
