import re
from collections import Counter

def run():
    with open("final_corpus.txt", "r", encoding="utf-8") as f:
        text = f.read()

    words = re.findall(r'[ء-ي]+', text)
    counts = Counter(words)

    suspects = Counter()
    for w in counts:
        if len(w) < 4: continue
        # Strip common legitimate prefixes for 'ال' like 'ب', 'ف', 'و', 'ك', 'لل', 'بال', 'فال', 'وال', 'كال'
        w_core = re.sub(r'^(و|ف|ب|ك|لل)?(ال)?', '', w)
        if len(w_core) < 4: continue
        
        for i in range(1, len(w_core) - 1):
            if w_core[i:i+2] == 'ال':
                suspects[w] += counts[w]

    print("Top words with 'ال' in the middle (could be 'لا' swaps):")
    for w, c in suspects.most_common(100):
        print(f"{w}: {c}")

if __name__ == "__main__":
    run()
