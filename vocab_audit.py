import re
from collections import Counter

def run_audit():
    with open("final_corpus.txt", "r", encoding="utf-8") as f:
        text = f.read()

    words = re.findall(r'[ء-ي]+', text)
    counts = Counter(words)

    # 1. Look for remaining words containing 'ال' not at the start
    mid_al = []
    for w in counts:
        stripped = re.sub(r'^(و|ف|ب|ك|لل|ل)?ال', '', w)
        if 'ال' in stripped and len(w) >= 5:
            mid_al.append(w)

    print("--- Top Remaining Internal 'ال' Words (Could be missed 'لا') ---")
    for w in sorted(mid_al, key=lambda x: -counts[x])[:60]:
        print(f"{w}: {counts[w]}")

    # 2. Look for any suspicious words that might be 'لا' -> 'ال'
    # We can check pairs of (word with ال, word with لا) and see if one exists
    # but let's just print a longer list to manually spot them.

if __name__ == "__main__":
    run_audit()
