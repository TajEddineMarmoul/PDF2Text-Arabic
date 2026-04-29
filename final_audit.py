import glob
import fitz
import re
from collections import Counter
from pdf2text_arabic._extract import extract_page

def run_audit():
    all_text = ""
    processed_files = []
    
    # Extract from all PDFs
    for p in glob.glob("download/*.pdf"):
        print(f"Processing {p}...")
        processed_files.append(p)
        doc = fitz.open(p)
        for p_num in range(len(doc)):
            page = doc.load_page(p_num)
            text, _ = extract_page(page)
            all_text += text + "\n"
        doc.close()
        
    with open("final_corpus.txt", "w", encoding="utf-8") as f:
        f.write(all_text)
        
    print(f"\nSuccessfully processed {len(processed_files)} files.")
    print("Files read:")
    for f in processed_files:
        print(f" - {f}")
        
    # Analyze errors
    print("\n--- Remaining Anomalies Analysis ---")
    
    words = re.findall(r'[ء-ي]+', all_text)
    counts = Counter(words)
    
    # 1. Words containing 'ال' in the middle (could be missed Lam-Alef swaps)
    # We ignore standard prefixes like بال, فال, كال, وال, لل
    mid_al = []
    for w in counts:
        # Strip common prefixes that legitimately precede 'ال'
        stripped = re.sub(r'^(و|ف|ب|ك|لل)?ال', '', w)
        if 'ال' in stripped and len(w) >= 5:
            mid_al.append(w)
            
    print("\n1. Top remaining words with internal 'ال' (Potential missed AL->LA swaps):")
    for w in sorted(mid_al, key=lambda x: -counts[x])[:20]:
        print(f"   {w}: {counts[w]}")
        
    # 2. Spacing issues (e.g. single isolated letters surrounded by spaces, excluding conjunctions)
    isolated_letters = re.findall(r'(?<![ء-ي])([أإابتثجحخدذرزسشصضطظعغفقكلمنهوي])(?![ء-ي])', all_text)
    isolated_counts = Counter(isolated_letters)
    # filter out 'و', 'ف', 'ب', 'ك', 'ل', 'أ' which can sometimes legitimately stand alone or are typos for prefixes
    weird_isolated = {k: v for k, v in isolated_counts.items() if k not in 'وفبكلأم'}
    print("\n2. Suspicious isolated letters (Potential spacing/OCR drops):")
    for k, v in sorted(weird_isolated.items(), key=lambda x: -x[1])[:10]:
        print(f"   '{k}': {v}")
        
    # 3. Words starting with 'امل' (missed AML -> ALM)
    start_aml = [w for w in counts if w.startswith('امل') and len(w) >= 4]
    print("\n3. Remaining words starting with 'امل' (Potential missed امل -> الم):")
    for w in sorted(start_aml, key=lambda x: -counts[x])[:10]:
        print(f"   {w}: {counts[w]}")

    # 4. Repeated words (e.g., عن عن)
    repeated = re.findall(r'\b([ء-ي]{2,})\s+\1\b', all_text)
    repeated_counts = Counter(repeated)
    print("\n4. Most common immediate word repetitions:")
    for k, v in sorted(repeated_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"   {k} {k}: {v}")

    # 5. Broken words with spaces in them (heuristics)
    # Look for 1-2 letter words followed by 3+ letter words that might belong together
    # e.g. "الضر ائب" -> "الضر" "ائب"
    fragments = re.findall(r'(?<![ء-ي])([ال]{2}|[ء-ي]{1,2})\s+([ء-ي]{3,})(?![ء-ي])', all_text)
    frag_counts = Counter(fragments)
    print("\n5. Suspicious split words (Potential spacing errors like 'الضر ائب'):")
    # Filter out common valid pairs like "في المغرب", "من الدستور"
    valid_starts = {'في', 'من', 'إلى', 'على', 'عن', 'ما', 'لا', 'يا', 'يا', 'لو', 'أن', 'إن', 'أو', 'أم', 'هل', 'بل', 'قد', 'لم', 'لن', 'كي'}
    suspicious_frags = {k: v for k, v in frag_counts.items() if k[0] not in valid_starts}
    for k, v in sorted(suspicious_frags.items(), key=lambda x: -x[1])[:15]:
        print(f"   {k[0]} {k[1]}: {v}")

if __name__ == "__main__":
    run_audit()
