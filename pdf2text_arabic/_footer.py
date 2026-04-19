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


def _collect_superscript_tips(page: fitz.Page, clip: fitz.Rect, body_size: float) -> set[str]:
    """Find all small superscript digits in the body text area."""
    # Look at the top 90% of the page to find tips (superscripts)
    body_clip = fitz.Rect(clip.x0, clip.y0, clip.x1, clip.y0 + (clip.y1 - clip.y0) * 0.9)
    data = page.get_text("rawdict", clip=body_clip)
    
    tips = set()
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
                        # STANDALONE check: if the whole line is small, it's likely a tip
                        is_tip = True
                        
                    if is_tip:
                        tips.add(digit_match)
    return tips


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
                        if table_bboxes and any(t.y0 - 2 <= y <= t.y1 + 2 and t.x0 <= (p1.x + p2.x)/2 <= t.x1 for t in table_bboxes):
                            continue
                        if clip.y0 < y < clip.y1 and y > (clip.y0 + (clip.y1 - clip.y0) * 0.2):
                            if best_y is None or y < best_y:
                                best_y = y
            elif item[0] == "re": # rectangle
                rect = item[1]
                if rect.height < 3.0 and rect.width >= min_line_width:
                    y = rect.y0
                    if table_bboxes and any(t.y0 - 2 <= y <= t.y1 + 2 and t.x0 <= rect.x0 + rect.width/2 <= t.x1 for t in table_bboxes):
                        continue
                    if clip.y0 < y < clip.y1 and y > (clip.y0 + (clip.y1 - clip.y0) * 0.2):
                        if best_y is None or y < best_y:
                            best_y = y
    return best_y


def _detect_footer_by_text_line(page: fitz.Page, clip: fitz.Rect) -> float | None:
    """Strategy 2: Detect text-based separator lines (e.g. '---', '___', or long space strings)."""
    dict_data = page.get_text("dict", clip=clip)
    best_y = None
    
    for block in dict_data.get("blocks", []):
        if block.get("type") != 0: continue
        for line in block.get("lines", []):
            if not line.get("spans"): continue
            line_text = "".join(span.get("text", "") for span in line["spans"]).strip()
            # We also care about lines that are purely whitespace if they are long
            raw_line_text = "".join(span.get("text", "") for span in line["spans"])
            
            y = line["bbox"][1]
            
            # 1. Check for standard text lines (dashes, underscores, dots)
            stripped = line_text.replace(" ", "")
            is_text_line = len(stripped) >= 10 and all(c in '_-ـ.' for c in stripped)
            
            # 2. Check for long whitespace lines (at least 30 spaces)
            is_space_line = not stripped and len(raw_line_text) >= 30
            
            if is_text_line or is_space_line:
                if y > (clip.y0 + (clip.y1 - clip.y0) * 0.2):
                    if best_y is None or y < best_y:
                        best_y = y
    return best_y


def _detect_footer_by_smart_markers(page, clip: fitz.Rect, tips: set[str], footnote_size: float) -> float | None:
    """Strategy 3: Match superscript tips to footnote starting lines."""
    if not tips:
        return None
        
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
            
            # Calculate dominant size for upward expansion
            lsizes = {}
            for s in line["spans"]:
                t = s.get("text", "").strip()
                if t:
                    sz = round(s.get("size", 0))
                    lsizes[sz] = lsizes.get(sz, 0) + len(t)
            ldom = max(lsizes.items(), key=lambda x: x[1])[0] if lsizes else footnote_size
            lines_info.append((y, line_text, ldom))

            for val in tips:
                # FOOTER RULE: Must start with "number-" or "numberـ" (dash)
                # We EXPLICITLY ignore "number)" or "number )" which are body lists.
                if line_text.startswith(val):
                    rest = line_text[len(val):].strip()
                    is_marker = False
                    if rest.startswith("-") or rest.startswith("ـ"):
                        is_marker = True
                    elif rest.startswith("."):
                        after_dot = rest[1:].lstrip()
                        if not after_dot or len(after_dot) < len(rest[1:]):
                            is_marker = True
                            
                    if is_marker:
                        if y > (clip.y0 + (clip.y1 - clip.y0) * 0.2):
                            gap_rect = fitz.Rect(clip.x0, y - 25, clip.x1, y - 1)
                            if not page.get_text("text", clip=gap_rect).strip():
                                if best_y is None or y < best_y:
                                    best_y = y
                        break
                        
    # Upward Expansion
    if best_y is not None:
        lines_info.sort(key=lambda x: x[0])
        idx = -1
        for i, (ly, _, _) in enumerate(lines_info):
            if ly == best_y:
                idx = i
                break
        if idx > 0:
            for i in range(idx - 1, -1, -1):
                py, pt, psz = lines_info[i]
                if psz <= footnote_size + 0.5:
                    best_y = py
                else:
                    break
                    
    return best_y


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
            relative_y = (y - clip.y0) / page_height
            required_ratio = 0.90 if relative_y < 0.7 else 0.70
            if ratio >= required_ratio and y > clip.y0 + page_height * 0.3:
                # GOLDEN RULE: Must have a spatial gap above it (at least 20px)
                gap_rect = fitz.Rect(clip.x0, y - 20, clip.x1, y - 1)
                if not page.get_text("text", clip=gap_rect).strip():
                    return y
    return None


def detect_footer_y(
    page: fitz.Page, 
    clip: fitz.Rect, 
    table_bboxes: list[fitz.Rect] | None = None
) -> tuple[float | None, bool]:
    """Find the y-coordinate where footnotes begin within *clip*.
    
    FOOTER RULE: Detection is only active if the page contains superscript 
    markers (tips) in the body text.
    """
    raw_data = page.get_text("rawdict", clip=clip)
    body_size = _get_body_size(raw_data)
    tips = _collect_superscript_tips(page, clip, body_size)

    # GOLDEN RULE: If no superscript markers found, we assume no footnotes exist.
    if not tips:
        return None, False

    # 1. Visual Line (Drawings)
    y = _detect_footer_by_line(page, clip, table_bboxes=table_bboxes)
    if y is not None:
        # GOLDEN RULE: A line is only a footer separator if a tip is found BELOW it.
        # This prevents mid-page lines from being flagged.
        below_clip = fitz.Rect(clip.x0, y, clip.x1, clip.y1)
        below_text = page.get_text("text", clip=below_clip).strip()
        # Verify that at least one tip is used as a marker (tip followed by dash)
        has_real_marker = False
        for tip in tips:
            # Look for "digit-" or "digitـ" at the start of a line
            if re.search(fr"^{re.escape(tip)}[\-ـ]", below_text, re.MULTILINE):
                has_real_marker = True
                break
        if has_real_marker:
            return y, True

    # 2. Text-based Line (Dashes, dots, or long spaces)
    y = _detect_footer_by_text_line(page, clip)
    if y is not None:
        below_clip = fitz.Rect(clip.x0, y, clip.x1, clip.y1)
        below_text = page.get_text("text", clip=below_clip).strip()
        has_real_marker = False
        for tip in tips:
            if re.search(fr"^{re.escape(tip)}[\-ـ]", below_text, re.MULTILINE):
                has_real_marker = True
                break
        if has_real_marker:
            return y, True

    # Calculate footnote size for remaining strategies
    sz_chars = _get_page_fonts(raw_data)
    fsize = None
    sorted_sz = sorted(sz_chars.items(), key=lambda x: x[1], reverse=True)
    for sz, count in sorted_sz:
        if sz <= body_size - 2.0 and count > sorted_sz[0][1] * 0.05:
            fsize = sz
            break

    # Strategy 3: Smart Marker Matching
    y = _detect_footer_by_smart_markers(page, clip, tips, fsize or body_size)
    if y is not None:
        return y, True

    # Strategy 4: Global Font Size Clustering
    y = _detect_footer_by_global_clustering(page, clip, body_size)
    if y is not None:
        return y, False

    return None, False
