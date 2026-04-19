import fitz
doc = fitz.open('download/قانون-المالية-2023.pdf')
page = doc[1]
blocks = page.get_text('dict')['blocks']
print(f"--- All text on Page 2 ---")
for b in blocks:
    if b['type'] != 0: continue
    for l in b['lines']:
        text = ''.join(s['text'] for s in l['spans'])
        print(f"Y={l['bbox'][1]:.1f} Size={l['spans'][0]['size']:.1f} Text={repr(text)}")
