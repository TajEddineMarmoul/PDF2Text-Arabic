import fitz
import re
from pdf2text_arabic._extract import extract_page
from pdf2text_arabic._text import merge_lines_by_y, is_arabic

def get_row_text(pdf_path, p_num, search_word):
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
            # Sort RTL
            sr.sort(key=lambda c: (-round(c["bbox"][0]), -c["bbox"][1]))
            
            # Generalized Native Fix:
            # Any zero-width character (width < 1.0) that overlaps with the next character
            # should be swapped to come AFTER the wide character.
            i = 0
            while i < len(sr) - 1:
                ch1, ch2 = sr[i], sr[i+1]
                w1 = ch1["bbox"][2] - ch1["bbox"][0]
                w2 = ch2["bbox"][2] - ch2["bbox"][0]
                # In RTL, ch1 is to the right (larger bbox[0]). 
                # If ch1 is zero-width and sits on the right edge of ch2:
                if w1 < 1.0 and w2 >= 1.0:
                    # check if they overlap (ch1 is within or on the boundary of ch2)
                    if ch2["bbox"][0] - 2 <= ch1["bbox"][0] <= ch2["bbox"][2] + 2:
                        # Swap!
                        ch1["bbox"] = ch2["bbox"]
                        sr[i], sr[i+1] = sr[i+1], sr[i]
                        i += 1
                i += 1
                
            text_str = "".join(c["c"] for c in sr)
            if search_word in text_str:
                print(f"FIXED: {text_str.strip()}")

get_row_text(r"download\قانون-المالية-2023.pdf", 1, "البرلمان")
get_row_text(r"download\-ظهير شريف رقم 1.14.44 بروتوكول الاتفاقية الدولية لسلامة الأرواح-1748340514821.pdf", 9, "الملاحية")

