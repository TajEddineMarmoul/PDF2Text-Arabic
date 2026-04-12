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

def _detect_footer_by_line(page, clip: fitz.Rect) -> float | None:
    """Strategy 1: Detect horizontal separator line."""
    page_width = clip.x1 - clip.x0
    min_line_width = page_width * 0.15 # Line must be at least 15% of page width
    
    drawings = page.get_drawings()
    best_y = None
    
    for drawing in drawings:
        for item in drawing.get("items", []):
            if item[0] == "l": # line
                p1, p2 = item[1], item[2]
                # Check if it's strictly horizontal (or very close)
                if abs(p1.y - p2.y) < 2.0:
                    width = abs(p1.x - p2.x)
                    if width >= min_line_width:
                        y = max(p1.y, p2.y)
                        # Ensure it's within the clip and in the lower 80% to avoid headers
                        if clip.y0 < y < clip.y1 and y > (clip.y0 + (clip.y1 - clip.y0) * 0.2):
                            if best_y is None or y < best_y:
                                best_y = y
            elif item[0] == "re": # rectangle (sometimes lines are thin rects)
                rect = item[1]
                if rect.height < 3.0 and rect.width >= min_line_width:
                    y = rect.y0
                    if clip.y0 < y < clip.y1 and y > (clip.y0 + (clip.y1 - clip.y0) * 0.2):
                        if best_y is None or y < best_y:
                            best_y = y
    return best_y

def _detect_footer_by_smart_markers(page, clip: fitz.Rect) -> float | None:
    """Strategy 2: Match superscripts in body to footnote lines.
    Also detects text-based separator lines (e.g., '___' or '---') and 
    expands upwards to include unnumbered footnote paragraphs.
    """
    data = page.get_text("rawdict", clip=clip, flags=fitz.TEXT_PRESERVE_WHITESPACE)
    
    # Get global font sizes to determine body vs superscript
    size_chars = _get_page_fonts(data)
    if not size_chars:
        return None
        
    # Get the top two font sizes by character count
    sorted_sizes = sorted(size_chars.items(), key=lambda x: x[1], reverse=True)
    if not sorted_sizes:
        return None
        
    primary_size = sorted_sizes[0][0]
    # If there's a second distinct size that has a reasonable amount of text (e.g., > 10% of primary)
    secondary_size = None
    for sz, count in sorted_sizes[1:]:
        if abs(sz - primary_size) >= 1 and count > sorted_sizes[0][1] * 0.1:
            secondary_size = sz
            break
            
    # The larger of the two is the body size, the smaller is the footnote size
    if secondary_size:
        body_size = max(primary_size, secondary_size)
        footnote_size = min(primary_size, secondary_size)
    else:
        body_size = primary_size
        footnote_size = primary_size # Fallback if only one size exists
        
    superscript_threshold = body_size * 0.85

    # 1. Collect potential superscript digits
    superscript_values: set[str] = set()
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                sz = span.get("size", 0)
                if sz > superscript_threshold or sz > 13:
                    continue
                txt = "".join(c.get("c", "") for c in span.get("chars", [])).strip()
                if txt.isdigit():
                    superscript_values.add(txt)

    # 2. Find text-based lines or lines starting with superscript digits
    dict_data = page.get_text("dict", clip=clip)
    best_y = None
    
    # Store lines to allow for "Upward Expansion"
    # Format: [(y, text, dominant_size)]
    lines_info = []
    
    for block in dict_data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            if not line.get("spans"):
                continue
            
            # Combine spans to form the line text, ignoring leading whitespace
            line_text = "".join(span.get("text", "") for span in line["spans"]).strip()
            if not line_text:
                continue
                
            y = line["bbox"][1] # Top Y of the line
            
            # Calculate dominant size for this specific line (for Upward Expansion)
            line_size_chars = {}
            for span in line["spans"]:
                txt = span.get("text", "").strip()
                if txt:
                    sz = round(span.get("size", 0))
                    line_size_chars[sz] = line_size_chars.get(sz, 0) + len(txt)
            line_dominant_size = max(line_size_chars.items(), key=lambda x: x[1])[0] if line_size_chars else footnote_size
            
            lines_info.append((y, line_text, line_dominant_size))
            
            # Check for text-based separator line (e.g., '_________', '---------', '.........')
            # Must be at least 10 chars long and consist almost entirely of line-drawing characters
            stripped_line = line_text.replace(" ", "")
            if len(stripped_line) >= 10 and all(c in '_-ـ.' for c in stripped_line):
                # Ensure it's in the lower 80% of the page
                if y > (clip.y0 + (clip.y1 - clip.y0) * 0.2):
                    if best_y is None or y < best_y:
                        best_y = y
                continue # If it's a line, no need to check for superscripts

            if not superscript_values:
                continue

            for val in superscript_values:
                # Check if line starts with the value followed by common separators or space
                if line_text.startswith(val):
                    rest = line_text[len(val):].strip()
                    if rest.startswith("-") or rest.startswith("ـ") or rest.startswith(".") or not rest:
                        # We found a matching footnote line
                        if best_y is None or y < best_y:
                            best_y = y
                        break
                        
    # 3. Upward Expansion
    # If we found a marker (like '55-'), check the lines immediately above it.
    # If they are unnumbered paragraphs using the small footnote font, include them in the footer.
    if best_y is not None and secondary_size is not None:
        # Sort lines by Y to walk upwards
        lines_info.sort(key=lambda x: x[0])
        
        # Find the index of the line that matches best_y
        marker_index = -1
        for i, (y, _, _) in enumerate(lines_info):
            if y == best_y:
                marker_index = i
                break
                
        if marker_index > 0:
            # Walk upwards from the marker
            for i in range(marker_index - 1, -1, -1):
                prev_y, prev_text, prev_size = lines_info[i]
                
                # If the line above is the small footnote font (with a small tolerance)
                if prev_size <= footnote_size + 0.5:
                    # Move the boundary up!
                    best_y = prev_y
                else:
                    # We hit the larger body text. Stop expanding upwards.
                    break

    return best_y

def _detect_footer_by_global_clustering(page, clip: fitz.Rect) -> float | None:
    """Strategy 3: Global font size clustering."""
    data = page.get_text("dict", clip=clip)
    
    # Calculate character counts per font size for the whole page
    size_chars: dict[int, int] = {}
    lines_info = [] # (y, dominant_size, text)
    
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
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

    if not size_chars or len(size_chars) < 2 or len(lines_info) < 3:
        return None
        
    # Get the top two font sizes
    sorted_sizes = sorted(size_chars.items(), key=lambda x: x[1], reverse=True)
    size1 = sorted_sizes[0][0]
    
    size2 = None
    for sz, count in sorted_sizes[1:]:
        if abs(sz - size1) >= 1 and count > sorted_sizes[0][1] * 0.05: # At least 5% of dominant
            size2 = sz
            break
            
    if not size2:
        return None # Only one meaningful font size on page
        
    body_size = max(size1, size2)
    footnote_size = min(size1, size2)
    
    # Find the transition point (top-down)
    # We want to find the highest Y where the line is footnote_size AND 
    # most subsequent text is also footnote_size.
    lines_info.sort(key=lambda x: x[0])
    
    for i, (y, sz, text) in enumerate(lines_info):
        # Allow a small tolerance for "footnote_size"
        if sz <= footnote_size + 0.5:
            # Check if this is a sustained transition
            remaining_lines = lines_info[i:]
            if not remaining_lines:
                continue
                
            small_count = sum(1 for _, s, _ in remaining_lines if s <= footnote_size + 0.5)
            if small_count / len(remaining_lines) >= 0.70:
                # To prevent falsely flagging an isolated small text block high up,
                # ensure we are at least below the top 30% of the page
                page_height = clip.y1 - clip.y0
                if y > clip.y0 + page_height * 0.3:
                    return y
                    
    return None

def detect_footer_y(page, clip: fitz.Rect) -> tuple[float | None, bool]:
    """Find the y-coordinate where footnotes begin within *clip*.

    Returns ``(y, guaranteed)`` where *guaranteed* is ``True`` when the
    footer was found via highly reliable indicators (Line or Smart Marker).
    """
    
    # Strategy 1: Visual Line
    y = _detect_footer_by_line(page, clip)
    if y is not None:
        return y, True

    # Strategy 2: Smart Marker Matching
    y = _detect_footer_by_smart_markers(page, clip)
    if y is not None:
        return y, True

    # Strategy 3: Global Font Size Clustering
    y = _detect_footer_by_global_clustering(page, clip)
    if y is not None:
        return y, False

    return None, False
