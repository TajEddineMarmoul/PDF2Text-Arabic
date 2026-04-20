import fitz
import sys

try:
    doc = fitz.open('download/قانون-المالية-2023.pdf')
    page = doc[16]
    tabs = page.find_tables(vertical_strategy="lines", horizontal_strategy="text")
    print(f"Number of tables found with mixed strategy: {len(tabs.tables)}")
    for t in tabs.tables:
        print(f"rows={len(t.rows)}, cols={len(t.header.cells)}, bbox={t.bbox}")
    doc.close()
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)