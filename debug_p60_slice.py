import fitz
import re
from pdf2text_arabic._extract import _compute_clip
from pdf2text_arabic._text import build_row_text, clean_arabic, merge_lines_by_y

doc = fitz.open(r"download/قانون-المالية-2023.pdf")
page = doc[59] # Page 60
clip = _compute_clip(page, 8.0, 4.5, "pct", True, True)

tabs = page.find_tables(clip=clip)
t = tabs.tables[0]

table_rawdict = page.get_text("rawdict", clip=fitz.Rect(t.bbox))

def _slice_region_into_rows(rawdict: dict, table, tx0: float, tx1: float) -> list[list[str]]:
    rows_map = {}
    ncells = len(table.header.cells)
    
    col_bounds = []
    for cell in table.rows[0].cells:
        if cell:
            col_bounds.append((cell[0], cell[2]))
        else:
            col_bounds.append((None, None))
            
    for ci, bounds in enumerate(reversed(col_bounds)):
        if bounds[0] is None:
            continue
        cx0, cx1 = bounds
        
        lines_all = []
        for block in rawdict.get("blocks", []):
            if "lines" not in block:
                continue
            for line in block["lines"]:
                filtered_spans = []
                for span in line["spans"]:
                    filtered_chars = []
                    for ch in span["chars"]:
                        bb = ch["bbox"]
                        char_cx = (bb[0] + bb[2]) / 2
                        if cx0 - 2.0 <= char_cx <= cx1 + 2.0:
                            filtered_chars.append(ch)
                    if filtered_chars:
                        new_span = dict(span)
                        new_span["chars"] = filtered_chars
                        filtered_spans.append(new_span)
                if filtered_spans:
                    new_line = dict(line)
                    new_line["spans"] = filtered_spans
                    lines_all.append(new_line)

        if not lines_all:
            continue
        
        merged = merge_lines_by_y(lines_all)
        for row in merged:
            cy = row["cy"]
            text = clean_arabic(build_row_text(row["spans"])).strip()
            text = re.sub(r"^[\u0600-\u06FF]\s+(?=\d)", "", text)
            if text:
                found_y = None
                for ry in rows_map.keys():
                    if abs(ry - cy) < 5.0:
                        found_y = ry
                        break
                if found_y is None:
                    found_y = cy
                    rows_map[found_y] = {col_idx: "" for col_idx in range(ncells)}
                rows_map[found_y][ci] = text

    sorted_ys = sorted(rows_map.keys())
    grid = []
    for ry in sorted_ys:
        grid.append([rows_map[ry][ci] for ci in range(ncells)])
    return grid

print("--- Slicing Table by Y-Coordinate ---")
grid = _slice_region_into_rows(table_rawdict, t, t.bbox[0], t.bbox[2])

for i, row in enumerate(grid[:15]):
    print(f"Row {i}: {' | '.join(row)}")
