import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic._tables import extract_tables

doc = fitz.open(r"download/قانون-المالية-2023.pdf")

def run_test(p_num, label):
    page = doc[p_num]
    clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)
    print(f"\n--- {label} (Page {p_num+1}) ---")
    results, bboxes, state = extract_tables(page, clip=clip)
    if results:
        for i, (res, bbox) in enumerate(zip(results, bboxes)):
            lines = res[1].split('\n')
            print(f"Table {i+1} bbox: {bbox}, Rows: {len(lines)}")
            print(f"First row: {repr(lines[0][:100])}")
    else:
        print("No tables found.")

run_test(53, "PAGE 54")
run_test(16, "PAGE 17")
