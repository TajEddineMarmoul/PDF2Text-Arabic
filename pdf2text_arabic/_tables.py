"""Table detection, cell extraction, and formatting.

Uses PyMuPDF's find_tables() with rawdict-per-cell extraction for proper
Arabic text ordering.  Simple tables (≤6 cols) render as pipe-delimited
rows; complex tables (>6 cols) are split into sub-tables of 3 columns.
Merged cells are filled down to make each row self-contained.
"""

from __future__ import annotations

import re

import fitz

from ._text import build_row_text, clean_arabic, merge_lines_by_y


def _extract_cell_text(page, cell_bbox, extract_ref: str = "", rawdict=None) -> str:
    """Extract Arabic text from a table cell using the full rawdict pipeline.

    *extract_ref* is the raw visual-LTR text from find_tables().extract() for
    the same cell, used to detect stray trailing chars from lam-alef ligature
    artifacts that leak across cell boundaries.

    *rawdict* is an optional pre-fetched rawdict for the table region.  When
    supplied the expensive ``page.get_text("rawdict")`` call is skipped.
    """
    if cell_bbox is None:
        return ""
    x0, y0, x1, y1 = cell_bbox
    if rawdict is None:
        clip = fitz.Rect(cell_bbox)
        rawdict = page.get_text("rawdict", clip=clip)

    lines_all: list = []
    for block in rawdict["blocks"]:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            filtered_spans = []
            for span in line["spans"]:
                filtered_chars = []
                for ch in span["chars"]:
                    bb = ch["bbox"]
                    cx = (bb[0] + bb[2]) / 2
                    cy = (bb[1] + bb[3]) / 2
                    if x0 - 0.5 <= cx <= x1 + 0.5 and y0 - 0.5 <= cy <= y1 + 0.5:
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
        return ""

    rows = merge_lines_by_y(lines_all)
    rows.sort(key=lambda r: r["cy"])

    texts: list[str] = []
    for row in rows:
        text = build_row_text(row["spans"])
        text = clean_arabic(text).strip()
        if text:
            texts.append(text)

    result = " ".join(texts)

    # Fix lam-alef ligature artifacts that leak across cell boundaries.
    result = re.sub(r"^[\u0600-\u06FF]\s+(?=\d)", "", result)

    if extract_ref and result:
        ref_nchars = sum(1 for c in extract_ref if not c.isspace())
        res_nchars = sum(1 for c in result if not c.isspace())
        if res_nchars > ref_nchars and res_nchars - ref_nchars <= 2:
            diff = res_nchars - ref_nchars
            stripped = result
            for _ in range(diff):
                if stripped and stripped[-1] in "اأإآ":
                    stripped = stripped[:-1].rstrip()
                else:
                    break
            if stripped:
                result = stripped

    return result


def extract_tables(
    page,
    clip=None,
    strategy=None,
    prev_table_state: dict | None = None,
) -> tuple[list[tuple[float, str]], list[tuple], dict | None]:
    """Extract tables from a page using PyMuPDF's find_tables().

    Returns (table_entries, bboxes, last_table_state).
    """
    kwargs = {}
    
    # We pass the full page rect to PyMuPDF to ensure the structural grid
    # is perfectly analyzed. If we pass the cropped `clip`, PyMuPDF drops
    # outermost columns because their headers were cropped off!
    kwargs["clip"] = page.rect
    
    if strategy is not None:
        kwargs["strategy"] = strategy

    tabs = page.find_tables(**kwargs)
    
    candidates = []
    
    # Identify initial candidates from the default strategy
    initial_tables = [t for t in tabs.tables if len(t.rows) >= 2 or (len(t.rows) == 1 and len(t.header.cells) > 2)]
    
    if strategy is None:
        if initial_tables:
            candidates = initial_tables
        else:
            mixed_tabs = page.find_tables(vertical_strategy="lines", horizontal_strategy="text", clip=page.rect)
            for t in mixed_tabs.tables:
                if len(t.rows) >= 2 or (len(t.rows) == 1 and len(t.header.cells) > 2):
                    if len(t.header.cells) > 2:
                        candidates.append(t)
    else:
        candidates = initial_tables

    if not candidates:
        return [], [], None

    results: list[tuple[float, str]] = []
    bboxes: list[tuple] = []
    
    candidates.sort(key=lambda t: t.bbox[1])

    for i, table in enumerate(candidates):
        # Intersect the table bounding box with the user's clip
        # so we don't draw debug boxes or process text in the margins.
        t_bbox = fitz.Rect(table.bbox)
        if clip is not None:
            t_bbox = t_bbox & clip
            if t_bbox.is_empty:
                continue

        bboxes.append(tuple(t_bbox))
        raw_extract = table.extract()
        table_clip = fitz.Rect(table.bbox)
        # Use the user's clip for rawdict so we don't grab header/footer text!
        extract_clip = t_bbox if clip is not None else table_clip
        table_rawdict = page.get_text("rawdict", clip=extract_clip)

        grid: list[list[str]] = []
        
        # MANUAL Y-SLICING FOR 1-ROW TABLES
        if len(table.rows) == 1 and len(table.header.cells) > 2:
            rows_map: dict[float, dict[int, str]] = {}
            ncells = len(table.rows[0].cells)
            
            for ci, cell in enumerate(reversed(table.rows[0].cells)):
                orig_ci = ncells - 1 - ci
                if not cell:
                    continue
                x0, y0, x1, y1 = cell
                
                lines_all: list = []
                for block in table_rawdict["blocks"]:
                    if "lines" not in block:
                        continue
                    for line in block["lines"]:
                        filtered_spans = []
                        for span in line["spans"]:
                            filtered_chars = []
                            for ch in span["chars"]:
                                bb = ch["bbox"]
                                cx = (bb[0] + bb[2]) / 2
                                cy = (bb[1] + bb[3]) / 2
                                if x0 - 0.5 <= cx <= x1 + 0.5 and y0 - 0.5 <= cy <= y1 + 0.5:
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
                    # Fix lam-alef ligature artifacts
                    text = re.sub(r"^[\u0600-\u06FF]\s+(?=\d)", "", text)
                    if text:
                        # Snap to existing Y within 5 pixels
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
            merged: list[list[bool]] = []
            for ry in sorted_ys:
                grid.append([rows_map[ry][ci] for ci in range(ncells)])
                merged.append([False] * ncells)
                
        else:
            # Stretch outermost cells horizontally to ensure we don't lose text
            # that falls outside PyMuPDF's strict column boundaries.
            if clip is not None:
                for row in table.rows:
                    if not row.cells:
                        continue
                    if row.cells[0]:
                        row.cells[0] = (clip.x0, row.cells[0][1], row.cells[0][2], row.cells[0][3])
                    if row.cells[-1]:
                        row.cells[-1] = (row.cells[-1][0], row.cells[-1][1], clip.x1, row.cells[-1][3])
            
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
                        ref = raw_extract[ri][orig_ci] if raw_extract[ri][orig_ci] else ""
                        row_cells.append(
                            _extract_cell_text(
                                page, cell, extract_ref=ref, rawdict=table_rawdict
                            )
                        )
                        row_merged.append(False)
                grid.append(row_cells)
                merged.append(row_merged)

            # Fill down merged cells for self-contained rows
            for ri in range(1, len(grid)):
                for ci in range(len(grid[ri])):
                    if merged[ri][ci] and ci < len(grid[ri - 1]) and grid[ri - 1][ci]:
                        grid[ri][ci] = grid[ri - 1][ci]

        # STITCHING LOGIC
        # If this is the FIRST table on the page, check if it continues from prev page
        current_headers = grid[0]
        if i == 0 and prev_table_state:
            # Must have same column count
            if len(current_headers) == prev_table_state["col_count"]:
                # Check if it starts near the top of the page
                if table.bbox[1] < page.rect.height * 0.25:
                    # If current headers look like data (non-empty) or the table has no headers,
                    # we insert the remembered headers.
                    if not any(h.strip() for h in current_headers):
                        grid[0] = prev_table_state["headers"]
                    else:
                        # Even if there are headers, they might just be repeated labels.
                        # We use the previous state to maintain consistency.
                        pass

        # Fill down merged cells for self-contained rows
        for ri in range(1, len(grid)):
            for ci in range(len(grid[ri])):
                if merged[ri][ci] and ci < len(grid[ri - 1]) and grid[ri - 1][ci]:
                    grid[ri][ci] = grid[ri - 1][ci]

        _format_rag_table(grid, table.bbox[1], results)

    # Prepare state for next page
    last = candidates[-1]
    # Re-extract headers for the state to ensure they are the original ones
    last_raw = last.extract()
    last_table_rawdict = page.get_text("rawdict", clip=fitz.Rect(last.bbox))
    
    final_headers = []
    for cell in reversed(last.rows[0].cells):
        if cell:
            final_headers.append(_extract_cell_text(page, cell, rawdict=last_table_rawdict))
        else:
            final_headers.append("")

    last_table_state = {
        "headers": final_headers,
        "col_count": len(final_headers),
        "y1": last.bbox[3]
    }

    return results, bboxes, last_table_state


def _format_rag_table(
    grid: list[list[str]],
    y_top: float,
    results: list[tuple[float, str]],
) -> None:
    """Render a table in a simple CSV-like format.

    This avoids the fragility of guessing headers, while still giving 
    the LLM clear column alignment via the ' | ' separator.
    Tags are omitted so that artificially split tables (e.g. across pages)
    naturally flow together in the LLM's context window.
    """
    if not grid or len(grid) < 2:
        return

    blocks: list[str] = []
    
    for row in grid:
        # Skip entirely empty rows
        if not any(c.strip() for c in row):
            continue
            
        cleaned_cells = []
        for cell in row:
            # Replace newlines and tabs with spaces to keep the cell on one line
            clean_cell = re.sub(r'[\r\n\t]+', ' ', cell.strip())
            # Replace multiple spaces with a single space
            clean_cell = re.sub(r' +', ' ', clean_cell)
            cleaned_cells.append(clean_cell)
            
        # Join cells with a clear delimiter
        row_text = " | ".join(cleaned_cells)
        blocks.append(row_text)
        
    # Only append if we have actual data rows
    if blocks:
        results.append((y_top, "\n".join(blocks)))
