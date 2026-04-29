import glob
import fitz
from collections import Counter
from pdf2text_arabic._extract import extract_page
import re

def process():
    with open("corpus_dump.txt", "r", encoding="utf-8") as f:
        all_text = f.read()
    
    words = re.findall(r'[ء-ي]+', all_text)
    counts = Counter(words)
    
    # 1. Words containing 'ال' not at start
    mid_al = [w for w in counts if 'ال' in w[1:] and len(w) >= 5]
    print("\n--- Top 'ال' not at start (possible لا -> ال) ---")
    for w in sorted(mid_al, key=lambda x: -counts[x])[:60]:
        print(f"{w}: {counts[w]}")
        
    # 2. Endings analysis
    end_al_t = [w for w in counts if w.endswith('الت') and len(w) >= 5]
    print("\n--- Words ending in 'الت' ---")
    for w in sorted(end_al_t, key=lambda x: -counts[x])[:30]:
        print(f"{w}: {counts[w]}")
        
    end_al_h = [w for w in counts if w.endswith('الء') and len(w) >= 5]
    print("\n--- Words ending in 'الء' ---")
    for w in sorted(end_al_h, key=lambda x: -counts[x])[:10]:
        print(f"{w}: {counts[w]}")

    end_al_f = [w for w in counts if w.endswith('الف') and len(w) >= 5]
    print("\n--- Words ending in 'الف' ---")
    for w in sorted(end_al_f, key=lambda x: -counts[x])[:20]:
        print(f"{w}: {counts[w]}")
        
    end_al_m = [w for w in counts if w.endswith('الم') and len(w) >= 5]
    print("\n--- Words ending in 'الم' ---")
    for w in sorted(end_al_m, key=lambda x: -counts[x])[:20]:
        print(f"{w}: {counts[w]}")
        
if __name__ == "__main__":
    process()
