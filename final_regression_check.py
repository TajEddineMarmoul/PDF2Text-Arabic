import fitz
from pdf2text_arabic._extract import extract_page

doc = fitz.open(r"download/قانون-المالية-2023.pdf")

pages_to_check = {
    16: "Page 17 (Table missing bottom border)",
    17: "Page 18 (Reversed text with dots)",
    24: "Page 25 (False positive 1-column tables)",
    46: "Page 47 (False positive 2-column tables)",
    53: "Page 54 (Article misidentified as table)",
    57: "Page 58 (Side-by-side open tables)",
    59: "Page 60 (5-column grouped rows)",
}

for p_num, desc in pages_to_check.items():
    page = doc[p_num]
    text, _ = extract_page(page)
    lines = text.split("\n")
    
    table_rows = [l for l in lines if "|" in l]
    print(f"\n{'='*20} {desc} {'='*20}")
    print(f"Total lines: {len(lines)}")
    print(f"Table rows: {len(table_rows)}")
    
    if p_num == 16:
        print(f"Check: Should have ~71 table rows. Actual: {len(table_rows)}")
    elif p_num == 17:
        print("Check: 'مهيأة للبيع بالتجزئة' should not be backwards.")
        print(f"Sample: {repr(lines[2][:60])}")
    elif p_num == 24:
        print(f"Check: Should have 0 table rows. Actual: {len(table_rows)}")
    elif p_num == 46:
        print(f"Check: Should have 0 table rows. Actual: {len(table_rows)}")
    elif p_num == 53:
        print(f"Check: Should have ~15 table rows at the bottom. Actual: {len(table_rows)}")
    elif p_num == 57:
        print(f"Check: Should have ~60 table rows. Actual: {len(table_rows)}")
    elif p_num == 59:
        print(f"Check: Should have ~30 table rows. Actual: {len(table_rows)}")
