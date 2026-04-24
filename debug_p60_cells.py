import fitz
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic._tables import _extract_cell_text

doc = fitz.open(r"download/قانون-المالية-2023.pdf")

# We will look at Page 60 (index 59)
page = doc[59]
clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)

tabs = page.find_tables(clip=clip)
t = tabs.tables[0]

print(f"Table BBox: {t.bbox}")
print(f"Rows: {len(t.rows)}, Cols: {len(t.header.cells)}")

# Look at the first 5 rows
raw_extract = t.extract()
rawdict = page.get_text("rawdict", clip=clip)

for ri, row in enumerate(t.rows[:5]):
    print(f"\n--- Row {ri} ---")
    row_cells = []
    ncells = len(row.cells)
    for ci, cell in enumerate(reversed(row.cells)):
        orig_ci = ncells - 1 - ci
        if cell is None:
            row_cells.append("[EMPTY]")
        else:
            ref = raw_extract[ri][orig_ci] if raw_extract[ri][orig_ci] else ""
            extracted = _extract_cell_text(page, cell, extract_ref=ref, rawdict=rawdict)
            row_cells.append(f"[{repr(extracted)}]")
            print(f"  Col {ci} (orig {orig_ci}): {cell} -> {repr(extracted)}")
    print("  Final Row: " + " | ".join(row_cells))
