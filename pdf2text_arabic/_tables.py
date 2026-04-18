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
) -> tuple[list[tuple[float, str]], list[tuple]]:
    """Extract tables from a page using PyMuPDF's find_tables().

    Returns (table_entries, bboxes) where table_entries is a list of
    (y_top, table_text) tuples for positioning.
    """
    kwargs = {}
    if clip is not None:
        kwargs["clip"] = clip
    if strategy is not None:
        kwargs["strategy"] = strategy

    tabs = page.find_tables(**kwargs)
    if not tabs.tables:
        return [], []

    # Drop false positives from PyMuPDF's line-based detector: bordered
    # header strips and column frames come back as 1-row "tables" with a
    # single prose cell. A real table has ≥ 2 rows.
    candidates = [t for t in tabs.tables if len(t.rows) >= 2]
    if not candidates:
        return [], []

    results: list[tuple[float, str]] = []
    bboxes: list[tuple] = []
    for table in candidates:
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

        _format_rag_table(grid, table.bbox[1], results)

    return results, bboxes


def _format_rag_table(
    grid: list[list[str]],
    y_top: float,
    results: list[tuple[float, str]],
) -> None:
    """Render a table as row-wise key: value blocks for RAG ingestion.

    Logical rows that span multiple visual rows (empty ID column) are merged.
    Blocks are separated by '---' for clean vector database chunking.
    """
    if not grid or len(grid) < 2:
        return

    headers = grid[0]

    # 1. Merge continued rows (where first column/ID is empty)
    merged_rows: list[list[str]] = []
    for row in grid[1:]:
        # Skip entirely empty rows
        if not any(c.strip() for c in row):
            continue

        # If the first column (usually ID) is empty, merge text into the previous row
        if not row[0].strip() and merged_rows:
            prev = merged_rows[-1]
            for j in range(1, min(len(row), len(prev))):
                if row[j].strip():
                    # Append text with a space
                    prev[j] = (prev[j] + " " + row[j].strip()).strip()
        else:
            merged_rows.append([c.strip() for c in row])

    # 2. Format as Key-Value blocks
    blocks: list[str] = []
    for row in merged_rows:
        block_lines = []
        for i, cell in enumerate(row):
            if not cell.strip() or cell.strip() == "...":
                continue
            header = (
                headers[i]
                if i < len(headers) and headers[i].strip()
                else f"عمود {i + 1}"
            )
            block_lines.append(f"{header}: {cell.strip()}")

        if block_lines:
            # Wrap in separators for clear RAG retrieval
            blocks.append("---\n" + "\n".join(block_lines) + "\n---")

    if blocks:
        results.append((y_top, "\n\n".join(blocks)))
