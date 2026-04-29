import glob
import os
import re
import fitz
from collections import Counter
from pdf2text_arabic._extract import extract_page

def process_pdfs():
    all_text = ""
    for p in glob.glob("download/*.pdf"):
        print(f"Processing {p}...")
        doc = fitz.open(p)
        for p_num in range(len(doc)):
            page = doc.load_page(p_num)
            text, _ = extract_page(page)
            all_text += text + "\n"
        doc.close()
    
    with open("corpus_dump.txt", "w", encoding="utf-8") as f:
        f.write(all_text)
        
    words = re.findall(r'[ء-ي]+', all_text)
    counts = Counter(words)
    
    # Look for signatures of broken Lam-Alef
    print("\n--- Words containing 'ال' not at start ---")
    mid_al = [w for w in counts if 'ال' in w[1:] and len(w) >= 5]
    for w in sorted(mid_al, key=lambda x: -counts[x])[:50]:
        print(f"{w}: {counts[w]}")
        
    print("\n--- Words starting with 'امل' ---")
    start_aml = [w for w in counts if w.startswith('امل') and len(w) >= 4]
    for w in sorted(start_aml, key=lambda x: -counts[x])[:50]:
        print(f"{w}: {counts[w]}")

    print("\n--- Words starting with 'الال' ---")
    start_alal = [w for w in counts if w.startswith('الال') and len(w) >= 4]
    for w in sorted(start_alal, key=lambda x: -counts[x])[:50]:
        print(f"{w}: {counts[w]}")

if __name__ == "__main__":
    process_pdfs()
