import re

with open("pdf2text_arabic/_tables.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Insert the slicing function right before extract_tables
slicing_func = """
def _slice_region_into_rows(rawdict: dict, table, tx0: float, tx1: float) -> list[list[str]]:
    rows_map: dict[float, dict[int, str]] = {}
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

def extract_tables("""

content = content.replace("def extract_tables(", slicing_func)

# 2. Update the extraction loop to use the slicing function if newlines are detected
old_loop = """        table_rawdict = page.get_text("rawdict", clip=extract_clip)

        grid: list[list[str]] = []
        merged: list[list[bool]] = []
        for ri, row in enumerate(table.rows):
            row_cells = []
            row_merged = []
            ncells = len(row.cells)
            for ci, cell in enumerate(reversed(row.cells)):
                orig_ci = ncells - 1 - ci
                if cell is None:
                    row_cells.append("")
                    row_merged.append(True)
                else:
                    # Stretch outermost cells horizontally
                    cx0, cy0, cx1, cy1 = cell
                    if abs(cx0 - table.bbox[0]) < 5: cx0 = t_bbox.x0
                    if abs(cx1 - table.bbox[2]) < 5: cx1 = t_bbox.x1
                    stretched_cell = (cx0, cy0, cx1, cy1)
                    
                    ref = raw_extract[ri][orig_ci] if raw_extract[ri][orig_ci] else ""
                    row_cells.append(
                        _extract_cell_text(
                            page, stretched_cell, extract_ref=ref, rawdict=table_rawdict
                        )
                    )
                    row_merged.append(False)
            grid.append(row_cells)
            merged.append(row_merged)"""

new_loop = """        table_rawdict = page.get_text("rawdict", clip=extract_clip)

        grid: list[list[str]] = []
        merged: list[list[bool]] = []
        
        has_newlines = any("\\n" in (c or "") for row in raw_extract for c in row)

        if (len(table.rows) == 1 and len(table.header.cells) > 2) or has_newlines:
            ncells = len(table.header.cells)
            grid = _slice_region_into_rows(table_rawdict, table, t_bbox.x0, t_bbox.x1)
            for _ in grid:
                merged.append([False] * ncells)
        else:
            for ri, row in enumerate(table.rows):
                row_cells = []
                row_merged = []
                ncells = len(row.cells)
                for ci, cell in enumerate(reversed(row.cells)):
                    orig_ci = ncells - 1 - ci
                    if cell is None:
                        row_cells.append("")
                        row_merged.append(True)
                    else:
                        cx0, cy0, cx1, cy1 = cell
                        if abs(cx0 - table.bbox[0]) < 5: cx0 = t_bbox.x0
                        if abs(cx1 - table.bbox[2]) < 5: cx1 = t_bbox.x1
                        stretched_cell = (cx0, cy0, cx1, cy1)
                        
                        ref = raw_extract[ri][orig_ci] if raw_extract[ri][orig_ci] else ""
                        row_cells.append(
                            _extract_cell_text(
                                page, stretched_cell, extract_ref=ref, rawdict=table_rawdict
                            )
                        )
                        row_merged.append(False)
                grid.append(row_cells)
                merged.append(row_merged)"""

content = content.replace(old_loop, new_loop)

with open("pdf2text_arabic/_tables.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied successfully.")
