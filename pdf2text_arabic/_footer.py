"""Footer separator detection for Arabic PDF pages.

Detects the boundary between body text and footnotes using a waterfall strategy:

1. **Visual Line Detection** - Looks for a drawn horizontal line separating body and footnotes.
2. **Text Line Detection** - Looks for selectable separator lines (---, ___, or long space strings).
3. **Smart Marker Matching** - Looks for superscript digits in the text and matches them to footnote lines starting with those digits.
4. **Global Font Size Clustering** - Finds the top two font sizes on the page and detects the transition point.
"""

from __future__ import annotations

import re
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


def _get_body_size(data: dict) -> float:
    """Find the most frequent font size on the page."""
    size_chars = _get_page_fonts(data)
    if not size_chars:
        return 12.0
    return max(size_chars.items(), key=lambda x: x[1])[0]


def _collect_superscript_tips(page: fitz.Page, clip: fitz.Rect, body_size: float) -> dict[str, float]:
    """Find all small superscript digits and map them to their LOWEST Y-coordinate."""
    # Look at the top 90% of the page to find tips (superscripts)
    body_clip = fitz.Rect(clip.x0, clip.y0, clip.x1, clip.y0 + (clip.height * 0.9))
    data = page.get_text("rawdict", clip=body_clip)
    
    tips: dict[str, float] = {}
    for block in data.get("blocks", []):
        if block.get("type") != 0: continue
        for line in block.get("lines", []):
            # Calculate the dominant size in this specific line
            line_sizes: dict[float, int] = {}
            for span in line.get("spans", []):
                txt = "".join(c.get("c", "") for c in span.get("chars", [])).strip()
                if txt:
                    sz = span.get("size", 0)
                    line_sizes[sz] = line_sizes.get(sz, 0) + len(txt)
            
            if not line_sizes: continue
            line_dominant_size = max(line_sizes.items(), key=lambda x: x[1])[0]

            for span in line.get("spans", []):
                sz = span.get("size", 0)
                txt = "".join(c.get("c", "") for c in span.get("chars", [])).strip()
                digit_match = "".join(filter(str.isdigit, txt))
                
                if digit_match:
                    # GOLDEN RULE: To be a 'tip', it must be smaller than the neighbors
                    # in its own line, OR significantly smaller than the page body.
                    is_tip = False
                    if sz < line_dominant_size * 0.9:
                        is_tip = True
                    elif sz < body_size * 0.85 and sz < 13:
                        is_tip = True
                        
                    if is_tip:
                        y_bottom = span["bbox"][3]
                        # Track the LOWEST point (maximum Y) each reference number appears in the body
                        if digit_match not in tips or y_bottom > tips[digit_match]:
                            tips[digit_match] = y_bottom
    return tips


def _detect_footer_by_line(
    page: fitz.Page, 
    clip: fitz.Rect, 
    table_bboxes: list[fitz.Rect] | None = None
) -> float | None:
    """Strategy 1: Detect horizontal separator line."""
    page_width = clip.x1 - clip.x0
    min_line_width = page_width * 0.15 
    
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
                        if table_bboxes and any(t.y0 - 2 <= y <= t.y1 + 2 and t.x0 <= (p1.x + p2.x)/2 <= t.x1 for t in table_bboxes):
                            continue
                        # Focus on the bottom 25% of the page
                        if clip.y0 < y < clip.y1 and y > (clip.y1 - (clip.height * 0.25)):
                            if best_y is None or y < best_y:
                                best_y = y
            elif item[0] == "re": # rectangle
                rect = item[1]
                if rect.height < 3.0 and rect.width >= min_line_width:
                    y = rect.y0
                    if table_bboxes and any(t.y0 - 2 <= y <= t.y1 + 2 and t.x0 <= rect.x0 + rect.width/2 <= t.x1 for t in table_bboxes):
                        continue
                    if clip.y0 < y < clip.y1 and y > (clip.y1 - (clip.height * 0.25)):
                        if best_y is None or y < best_y:
                            best_y = y
    return best_y


def _detect_footer_by_text_line(page: fitz.Page, clip: fitz.Rect) -> float | None:
    """Strategy 2: Detect text-based separator lines (e.g. '---', '___')."""
    dict_data = page.get_text("dict", clip=clip)
    best_y = None
    
    for block in dict_data.get("blocks", []):
        if block.get("type") != 0: continue
        for line in block.get("lines", []):
            if not line.get("spans"): continue
            line_text = "".join(span.get("text", "") for span in line["spans"]).strip()
            raw_line_text = "".join(span.get("text", "") for span in line["spans"])
            y = line["bbox"][1]
            
            stripped = line_text.replace(" ", "")
            is_text_line = len(stripped) >= 10 and all(c in '_-ـ.' for c in stripped)
            is_space_line = not stripped and len(raw_line_text) >= 30
            
            if is_text_line or is_space_line:
                if y > (clip.y1 - (clip.height * 0.25)):
                    if best_y is None or y < best_y:
                        best_y = y
    return best_y


def _detect_footer_by_smart_markers(page, clip: fitz.Rect, tips: dict[str, float]) -> float | None:
    """Strategy 3: Topmost Linked Reference.
    
    Identifies the highest line in the footer area that starts with a number
    matching a superscript tip, ensuring the footer line is physically 
    below the lowest usage of that tip in the body.
    """
    if not tips:
        return None
        
    lowest_tip_y = max(tips.values())
    blocks = page.get_text("blocks", clip=clip)
    match_ys = []
    
    for b in blocks:
        bx0, by0, bx1, by1, text = b[:5]
        if by0 <= lowest_tip_y:
            continue
            
        match = re.match(r"^(\d+)", text.strip())
        if match:
            num = match.group(1)
            # COORDINATE LINKAGE: Marker must match a tip and sit below all body tips.
            if num in tips:
                match_ys.append(by0)

    if match_ys:
        # Return the HIGHEST (minimum Y) matching reference line
        return min(match_ys)
        
    return None


def _detect_footer_by_global_clustering(page, clip: fitz.Rect, body_size: float) -> float | None:
    """Strategy 4: Global font size clustering."""
    data = page.get_text("dict", clip=clip)
    lines_info = [] 
    size_chars = {}
    
    for block in data.get("blocks", []):
        if block.get("type") != 0: continue
        for line in block.get("lines", []):
            line_size_chars = {}
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

    if len(lines_info) < 3: return None
    
    # Footnote font must be at least 2pt smaller than body
    footnote_size = None
    sorted_sizes = sorted(size_chars.items(), key=lambda x: x[1], reverse=True)
    for sz, count in sorted_sizes:
        if sz <= body_size - 2.0 and count > sorted_sizes[0][1] * 0.05:
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
            if ratio >= 0.70 and y > (clip.y1 - page_height * 0.2):
                gap_rect = fitz.Rect(clip.x0, y - 20, clip.x1, y - 1)
                if not page.get_text("text", clip=gap_rect).strip():
                    return y
    return None


def detect_footer_y(
    page: fitz.Page, 
    clip: fitz.Rect, 
    table_bboxes: list[fitz.Rect] | None = None
) -> tuple[float | None, bool]:
    """Find the y-coordinate where footnotes begin using coordinate linkage."""
    raw_data = page.get_text("rawdict", clip=clip)
    body_size = _get_body_size(raw_data)
    # 1. Map Tips to their lowest Y-coordinates
    tips_map = _collect_superscript_tips(page, clip, body_size)

    # If no superscript markers found, we assume no footnotes exist.
    if not tips_map:
        return None, False

    # 2. Visual Line
    y = _detect_footer_by_line(page, clip, table_bboxes=table_bboxes)
    if y is not None:
        return y, True

    # 3. Text-based Line
    y = _detect_footer_by_text_line(page, clip)
    if y is not None:
        return y, True

    # 4. Strategy: Topmost Linked Reference (Using mapped coordinates)
    y = _detect_footer_by_smart_markers(page, clip, tips_map)
    if y is not None:
        return y, True

    # 5. Global Font Size Clustering
    y = _detect_footer_by_global_clustering(page, clip, body_size)
    if y is not None:
        return y, False

    return None, False
