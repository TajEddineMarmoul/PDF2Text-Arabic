"""Footer separator detection for Arabic PDF pages.

Detects the boundary between body text and footnotes using a waterfall strategy:

1. **Visual Line Detection** - Looks for a drawn horizontal line separating body and footnotes.
2. **Smart Marker Matching** - Looks for superscript digits in the text and matches them to footnote lines starting with those digits.
3. **Global Font Size Clustering** - Finds the top two font sizes on the page and detects the transition point.
"""

from __future__ import annotations

import fitz

_HEADING_SIZE_MIN = 20

def _get_page_fonts(data: dict) -> dict[int, int]:
    """Calculate character counts for each rounded font size on the page."""
    size_chars: dict[int, int] = {}
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                txt = "".join(c.get("c", "") for c in span.get("chars", [])).strip()
                if not txt:
                    continue
                sz = round(span.get("size", 0))
                if sz >= _HEADING_SIZE_MIN:
                    continue
                size_chars[sz] = size_chars.get(sz, 0) + len(txt)
    return size_chars

def _detect_footer_by_line(
    page: fitz.Page, 
    clip: fitz.Rect, 
    table_bboxes: list[fitz.Rect] | None = None
) -> float | None:
    """Strategy 1: Detect horizontal separator line."""
    page_width = clip.x1 - clip.x0
    min_line_width = page_width * 0.15 # Line must be at least 15% of page width
    
    drawings = page.get_drawings()
    best_y = None
    
    for drawing in drawings:
        for item in drawing.get("items", []):
            if item[0] == "l": # line
                p1, p2 = item[1], item[2]
                if abs(p1.y - p2.y) < 2.0:
                    width = abs(p1.x - p2.x)
                    if width >= min_line_width:
                        y = max(p1.y, p2.y)
                        
                        # SAFETY: Skip lines inside tables
                        if table_bboxes:
                            if any(t.y0 - 2 <= y <= t.y1 + 2 and t.x0 <= (p1.x + p2.x)/2 <= t.x1 for t in table_bboxes):
                                continue

                        # Ensure it's within the clip and in the lower 80% to avoid headers
                        if clip.y0 < y < clip.y1 and y > (clip.y0 + (clip.y1 - clip.y0) * 0.2):
                            if best_y is None or y < best_y:
                                best_y = y
            elif item[0] == "re": # rectangle
                rect = item[1]
                if rect.height < 3.0 and rect.width >= min_line_width:
                    y = rect.y0
                    
                    # SAFETY: Skip lines inside tables
                    if table_bboxes:
                        if any(t.y0 - 2 <= y <= t.y1 + 2 and t.x0 <= rect.x0 + rect.width/2 <= t.x1 for t in table_bboxes):
                            continue

                    if clip.y0 < y < clip.y1 and y > (clip.y0 + (clip.y1 - clip.y0) * 0.2):
                        if best_y is None or y < best_y:
                            best_y = y
    return best_y

def _detect_footer_by_smart_markers(page, clip: fitz.Rect) -> float | None:
    """Strategy 2: Match superscripts in body to footnote lines."""
    data = page.get_text("rawdict", clip=clip, flags=fitz.TEXT_PRESERVE_WHITESPACE)
    
    # Get global font sizes to determine body vs superscript
    size_chars = _get_page_fonts(data)
    if not size_chars: return None
    sorted_sizes = sorted(size_chars.items(), key=lambda x: x[1], reverse=True)
    if not sorted_sizes: return None
    primary_size = sorted_sizes[0][0]
    
    secondary_size = None
    for sz, count in sorted_sizes[1:]:
        if abs(sz - primary_size) >= 1 and count > sorted_sizes[0][1] * 0.1:
            secondary_size = sz
            break
            
    body_size = max(primary_size, secondary_size) if secondary_size else primary_size
    footnote_size = min(primary_size, secondary_size) if secondary_size else primary_size
    superscript_threshold = body_size * 0.85

    # 1. Collect potential superscript digits
    superscript_values: set[str] = set()
    for block in data.get("blocks", []):
        if block.get("type") != 0: continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                sz = span.get("size", 0)
                if sz > superscript_threshold or sz > 13: continue
                txt = "".join(c.get("c", "") for c in span.get("chars", [])).strip()
                if txt.isdigit(): superscript_values.add(txt)

    # 2. Find text-based lines or lines starting with superscript digits
    dict_data = page.get_text("dict", clip=clip)
    best_y = None
    lines_info = []
    
    for block in dict_data.get("blocks", []):
        if block.get("type") != 0: continue
        for line in block.get("lines", []):
            if not line.get("spans"): continue
            line_text = "".join(span.get("text", "") for span in line["spans"]).strip()
            if not line_text: continue
            y = line["bbox"][1]
            
            line_size_chars = {}
            for span in line["spans"]:
                txt = span.get("text", "").strip()
                if txt:
                    sz = round(span.get("size", 0))
                    line_size_chars[sz] = line_size_chars.get(sz, 0) + len(txt)
            line_dominant_size = max(line_size_chars.items(), key=lambda x: x[1])[0] if line_size_chars else footnote_size
            lines_info.append((y, line_text, line_dominant_size))
            
            stripped_line = line_text.replace(" ", "")
            if len(stripped_line) >= 10 and all(c in '_-ـ.' for c in stripped_line):
                if y > (clip.y0 + (clip.y1 - clip.y0) * 0.2):
                    if best_y is None or y < best_y: best_y = y
                continue

            for val in superscript_values:
                if line_text.startswith(val):
                    rest = line_text[len(val):].strip()
                    is_marker = False
                    if rest.startswith("-") or rest.startswith("ـ") or not rest:
                        is_marker = True
                    elif rest.startswith("."):
                        after_dot = rest[1:].lstrip()
                        if not after_dot or len(after_dot) < len(rest[1:]):
                            is_marker = True
                    if is_marker:
                        if best_y is None or y < best_y: best_y = y
                        break
                        
    if best_y is not None and secondary_size is not None:
        lines_info.sort(key=lambda x: x[0])
        marker_index = -1
        for i, (y, _, _) in enumerate(lines_info):
            if y == best_y:
                marker_index = i
                break
        if marker_index > 0:
            for i in range(marker_index - 1, -1, -1):
                prev_y, prev_text, prev_size = lines_info[i]
                if prev_size <= footnote_size + 0.5: best_y = prev_y
                else: break
    return best_y

def _detect_footer_by_global_clustering(page, clip: fitz.Rect) -> float | None:
    """Strategy 3: Global font size clustering."""
    data = page.get_text("dict", clip=clip)
    size_chars: dict[int, int] = {}
    lines_info = [] 
    
    for block in data.get("blocks", []):
        if block.get("type") != 0: continue
        for line in block.get("lines", []):
            line_size_chars: dict[int, int] = {}
            line_text = ""
            for span in line.get("spans", []):
                txt = span.get("text", "").strip()
                if txt:
                    sz = round(span.get("size", 0))
                    if sz < _HEADING_SIZE_MIN:
                        line_size_chars[sz] = line_size_chars.get(sz, 0) + len(txt)
                        size_chars[sz] = size_chars.get(sz, 0) + len(txt)
                    line_text += txt
            if line_size_chars:
                dominant_size = max(line_size_chars.items(), key=lambda x: x[1])[0]
                y = line["bbox"][1]
                lines_info.append((y, dominant_size, line_text))

    if not size_chars or len(lines_info) < 3: return None
    body_size = max(size_chars.items(), key=lambda x: x[1])[0]
    footnote_size = None
    sorted_sizes = sorted(size_chars.items(), key=lambda x: x[1], reverse=True)
    for sz, count in sorted_sizes:
        if sz <= body_size - 1.5 and count > sorted_sizes[0][1] * 0.05:
            footnote_size = sz
            break
    if not footnote_size: return None
    
    lines_info.sort(key=lambda x: x[0])
    for i, (y, sz, text) in enumerate(lines_info):
        if sz <= footnote_size + 0.5:
            remaining_lines = lines_info[i:]
            if not remaining_lines: continue
            small_count = sum(1 for _, s, _ in remaining_lines if s <= footnote_size + 0.5)
            ratio = small_count / len(remaining_lines)
            page_height = clip.y1 - clip.y0
            relative_y = (y - clip.y0) / page_height
            required_ratio = 0.90 if relative_y < 0.7 else 0.70
            if ratio >= required_ratio and y > clip.y0 + page_height * 0.3:
                return y
    return None

def detect_footer_y(
    page: fitz.Page, 
    clip: fitz.Rect, 
    table_bboxes: list[fitz.Rect] | None = None
) -> tuple[float | None, bool]:
    """Find the y-coordinate where footnotes begin within *clip*.

    Returns ``(y, guaranteed)`` where *guaranteed* is ``True`` when the
    footer was found via highly reliable indicators (Line or Smart Marker).
    """
    y = _detect_footer_by_line(page, clip, table_bboxes=table_bboxes)
    if y is not None: return y, True

    y = _detect_footer_by_smart_markers(page, clip)
    if y is not None: return y, True

    y = _detect_footer_by_global_clustering(page, clip)
    if y is not None: return y, False

    return None, False
