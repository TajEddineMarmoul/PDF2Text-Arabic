import fitz
from pdf2text_arabic._extract import _compute_clip

doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[20] # Page 21
clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)

print("--- PAGE 21: TRY CLIP FIRST ---")
tabs_clip = page.find_tables(clip=clip)
if tabs_clip.tables:
    for i, t in enumerate(tabs_clip.tables):
        print(f"Table {i+1} bbox: {t.bbox}, rows={len(t.rows)}")
else:
    print("No tables found with clip. Trying page.rect...")
    tabs_rect = page.find_tables(clip=page.rect)
    if tabs_rect.tables:
        for i, t in enumerate(tabs_rect.tables):
            print(f"Table {i+1} bbox: {t.bbox}, rows={len(t.rows)}")
    else:
        print("No tables found with page.rect either.")
