"""Table detection, cell extraction, and formatting.

Uses PyMuPDF's find_tables() with rawdict-per-cell extraction for proper
Arabic text ordering.  Simple tables (≤6 cols) render as pipe-delimited
rows; complex tables (>6 cols) are split into sub-tables of 3 columns.
Merged cells are filled down to make each row self-contained.
"""

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


def extract_tables(page, clip=None) -> tuple[list[tuple[float, str]], list[tuple]]:
    """Extract tables from a page using PyMuPDF's find_tables().

    Returns (table_entries, bboxes) where table_entries is a list of
    (y_top, table_text) tuples for positioning.
    """
    tabs = page.find_tables(clip=clip)
    if not tabs.tables:
        return [], []

    results: list[tuple[float, str]] = []
    bboxes: list[tuple] = []
    for table in tabs.tables:
        bboxes.append(table.bbox)

        raw_extract = table.extract()

        # Fetch rawdict once for the entire table region.
        table_clip = fitz.Rect(table.bbox)
        table_rawdict = page.get_text("rawdict", clip=table_clip)

        # Build grid with merged-cell tracking (RTL column order)
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

        ncols = table.col_count

        if ncols <= 6:
            _format_simple_table(grid, table.bbox[1], results)
        else:
            _format_complex_table(grid, merged, ncols, table.bbox[1], results)

    return results, bboxes


def _format_simple_table(
    grid: list[list[str]],
    y_top: float,
    results: list[tuple[float, str]],
) -> None:
    """Render a simple table (≤6 cols) as pipe-separated rows."""
    lines: list[str] = []
    for row in grid:
        line = " | ".join(c if c else "" for c in row)
        lines.append(line)
    results.append((y_top, "\n".join(lines)))


def _format_complex_table(
    grid: list[list[str]],
    merged: list[list[bool]],
    ncols: int,
    y_top: float,
    results: list[tuple[float, str]],
) -> None:
    """Split a complex table (>6 cols) into 3-column sub-tables."""
    group_size = 3
    n_groups = ncols // group_size

    for g in range(n_groups):
        start_col = g * group_size
        end_col = start_col + group_size

        group_header = ""
        if len(grid) > 1:
            for ci in range(start_col, min(end_col, len(grid[1]))):
                if grid[1][ci]:
                    group_header = grid[1][ci]
                    break

        lines = []
        if group_header:
            lines.append(group_header)

        if len(grid) > 2:
            header_cells = []
            for ci in range(start_col, min(end_col, ncols)):
                if ci < len(grid[2]):
                    header_cells.append(grid[2][ci] if grid[2][ci] else "")
                else:
                    header_cells.append("")
            lines.append(" | ".join(header_cells))

        for ri in range(3, len(grid)):
            row_cells = []
            all_empty = True
            all_merged = True
            for ci in range(start_col, min(end_col, ncols)):
                if ci < len(grid[ri]):
                    val = grid[ri][ci]
                    if val:
                        all_empty = False
                    if ci < len(merged[ri]) and not merged[ri][ci]:
                        all_merged = False
                    row_cells.append(val)
                else:
                    row_cells.append("")
            if not all_empty and not all_merged:
                lines.append(" | ".join(row_cells))

        if len(lines) > 1:
            results.append((y_top, "\n".join(lines)))
