import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic._tables import extract_tables

doc = fitz.open('download/قانون-المالية-2023.pdf')
for p_num in [16, 23, 24, 57, 115]:
    page = doc[p_num]
    clip = _compute_clip(page, 8.0, 4.5, 'pct', True, True)

    print(f"\n--- Debug Tables: Page {p_num+1} ---")
    results, bboxes, state = extract_tables(page, clip=clip)
    print(f"Extracted {len(results)} formatted tables")
    for r in results:
        lines = r[1].split('\n')
        for L in lines[:10]:
            print(L)
        print("...")

doc.close()