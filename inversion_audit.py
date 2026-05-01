import re
from collections import Counter

with open("final_corpus.txt", "r", encoding="utf-8") as f:
    text = f.read()

words = re.findall(r'[ء-ي]+', text)
counts = Counter(words)

# Lam-Meem vs Meem-Lam
# Look for words containing 'مل' where 'لم' is expected
# e.g., 'البرملان' -> 'البرلمان'
ml_words = [w for w in counts if 'مل' in w and w != 'عمل' and w != 'حمل']
print("--- Words with 'مل' (could be 'لم' inversions) ---")
for w in sorted(ml_words, key=lambda x: -counts[x])[:20]:
    print(f"{w}: {counts[w]}")

# Lam-Haa vs Haa-Lam
hl_words = [w for w in counts if 'هل' in w]
print("\n--- Words with 'هل' (could be 'له' inversions) ---")
for w in sorted(hl_words, key=lambda x: -counts[x])[:20]:
    print(f"{w}: {counts[w]}")

