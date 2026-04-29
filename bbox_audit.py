import fitz
from pdf2text_arabic._extract import extract_page
import json

doc = fitz.open(r"download\-ظهير شريف رقم 1.14.44 بروتوكول الاتفاقية الدولية لسلامة الأرواح-1748340514821.pdf")
# Page 10 is index 9
page = doc.load_page(9)
rawdict = page.get_text("rawdict")

from pdf2text_arabic._text import merge_lines_by_y, build_row_text, is_arabic
lines = []
for b in rawdict["blocks"]:
    if "lines" in b:
        lines.extend(b["lines"])

rows = merge_lines_by_y(lines)
for row in rows:
    all_chars = []
    for span in row["spans"]:
        all_chars.extend(span.get("chars", []))
    if not all_chars: continue
    all_chars.sort(key=lambda c: c["bbox"][1])
    
    subrows = []
    current_row = [all_chars[0]]
    for i in range(1, len(all_chars)):
        c = all_chars[i]
        if abs(c["bbox"][1] - current_row[-1]["bbox"][1]) < 3.0:
            current_row.append(c)
        else:
            subrows.append(current_row)
            current_row = [c]
    subrows.append(current_row)
    
    for sr in subrows:
        sr.sort(key=lambda c: (-round(c["bbox"][0]), -c["bbox"][1]))
        text_str = "".join(c["c"] for c in sr)
        if "المالحية" in text_str or "السالمة" in text_str:
            print("FOUND:", text_str.strip())
            print("Chars:")
            # Just print the relevant part
            idx = text_str.find("المالحية")
            if idx == -1: idx = text_str.find("السالمة")
            for c in sr[max(0, idx-2):min(len(sr), idx+10)]:
                print(f"Char: '{c['c']}', bbox: {c['bbox']}")
            print("---")
