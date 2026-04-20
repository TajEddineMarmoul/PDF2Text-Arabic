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


def _has_side_borders(page: fitz.Page, clip: fitz.Rect) -> bool:
    """True if the page contains vertical lines/segments at the left and right margins.
    
    Handles tables that have vertical lines but are missing horizontal borders 
    (e.g., top, bottom, or row separators).
    """
    drawings = page.get_drawings()
    left_segments = 0
    right_segments = 0
    
    # We look for vertical elements in the outer 15% of the clip width
    w = clip.width
    left_zone = (clip.x0, clip.x0 + w * 0.15)
    right_zone = (clip.x1 - w * 0.15, clip.x1)
    
    for d in drawings:
        r = d["rect"]
        # Must be inside our vertical clip
        if not (clip.y0 <= r.y0 <= clip.y1):
            continue
            
        # Vertical segment check: width < 5 (includes lines and thin rects)
        if r.width < 5:
            if left_zone[0] <= r.x0 <= left_zone[1]:
                left_segments += r.height
            elif right_zone[0] <= r.x0 <= right_zone[1]:
                right_segments += r.height
                
    # If we found substantial vertical markings on BOTH sides (at least 200px total height),
    # we consider it a structured table container.
    return left_segments > 200 and right_segments > 200


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
    if clip is not None:
        kwargs["clip"] = clip
    if strategy is not None:
        kwargs["strategy"] = strategy

    tabs = page.find_tables(**kwargs)
    
    # AUTO-FALLBACK: If the page has vertical borders OR if the default 'lines' strategy
    # found a table with many columns, horizontal row separators might be missing.
    # In these cases, we check if the 'text' strategy finds significantly more rows.
    if strategy is None:
        max_rows = 0
        max_cols = 0
        if tabs.tables:
            max_rows = max(len(t.rows) for t in tabs.tables)
            max_cols = max(len(t.header.cells) for t in tabs.tables)
            
        has_borders = False
        if clip is not None:
            has_borders = _has_side_borders(page, clip)
            
        # We try the fallback if there are explicit page borders, or if we already 
        # know it's a complex grid (>3 columns) that might be truncated.
        needs_fallback = has_borders or (max_cols > 3)
        
        if needs_fallback:
            text_tabs = page.find_tables(vertical_strategy="lines", horizontal_strategy="text", clip=clip)
            if text_tabs.tables:
                text_max_rows = max([len(t.rows) for t in text_tabs.tables])
                # Switch if the mixed strategy finds a significantly larger table
                if text_max_rows > max_rows + 2:
                    tabs = text_tabs

    if not tabs.tables:
        return [], [], None

    # New Rule: Must have at least 2 rows to be considered a table.
    # 1-row detections are usually just justified text lines.
    candidates = []
    for t in tabs.tables:
        rows = len(t.rows)
        if rows >= 2:
            candidates.append(t)
            
    if not candidates:
        return [], [], None

    results: list[tuple[float, str]] = []
    bboxes: list[tuple] = []
    
    # Sort candidates by vertical position
    candidates.sort(key=lambda t: t.bbox[1])

    for i, table in enumerate(candidates):
        bboxes.append(table.bbox)
        raw_extract = table.extract()
        table_clip = fitz.Rect(table.bbox)
        table_rawdict = page.get_text("rawdict", clip=table_clip)

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

        # Check if this row looks like a new main heading (e.g. contains "30.01")
        # usually found in the description column (which could be any column if others are empty)
        text_content = " ".join(c.strip() for c in row if c.strip())
        is_heading = bool(re.search(r'\b\d{2}\.\d{2}\b', text_content))

        # If the first column (usually ID) is empty, merge text into the previous row
        # UNLESS it is a new main heading.
        if not row[0].strip() and merged_rows and not is_heading:
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
