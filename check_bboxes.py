import fitz
from pdf2text_arabic._extract import extract_page
from pdf2text_arabic._text import merge_lines_by_y, is_arabic

def audit_word(pdf_path, p_num, target_word):
    doc = fitz.open(pdf_path)
    page = doc.load_page(p_num)
    rawdict = page.get_text("rawdict")
    
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
            # We sort exactly as we do before native fix
            sr_original = list(sr)
            sr_original.sort(key=lambda c: (-round(c["bbox"][0]), -c["bbox"][1]))
            text_str = "".join(c["c"] for c in sr_original)
            
            if target_word in text_str:
                print(f"FOUND {target_word} in: {text_str.strip()}")
                idx = text_str.find(target_word)
                print("Original Chars:")
                for c in sr_original[max(0, idx-2):min(len(sr_original), idx+len(target_word)+2)]:
                    width = c['bbox'][2] - c['bbox'][0]
                    print(f"Char: '{c['c']}', bbox: {c['bbox']}, width: {width:.2f}")
                print("---")

print("Checking البرملان")
audit_word(r"download\قانون-المالية-2023.pdf", 1, "البرملان")

print("Checking العجالت")
# Let's find العجالت first
import glob
for p in glob.glob("download/*.pdf"):
    doc = fitz.open(p)
    for i in range(len(doc)):
        text = doc.load_page(i).get_text("text")
        if "العجالت" in text:
            audit_word(p, i, "العجالت")
    doc.close()
