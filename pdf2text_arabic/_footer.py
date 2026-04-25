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


def _span_text(span: dict) -> str:
    return "".join(c.get("c", "") for c in span.get("chars", [])).strip()


def _has_letters(text: str) -> bool:
    return any(c.isalpha() for c in text)


def _dominant_size(spans: list[dict]) -> float:
    size_chars: dict[float, int] = {}
    for span in spans:
        txt = _span_text(span)
        if txt:
            sz = span.get("size", 0)
            size_chars[sz] = size_chars.get(sz, 0) + len(txt)
    if not size_chars:
        return 0
    return max(size_chars.items(), key=lambda x: x[1])[0]


def _reference_marker_number(text: str) -> str | None:
    compact = re.sub(r"\s+", "", text.strip())
    match = re.match(r"^(\d+)", compact)
    if not match:
        return None
    num = match.group(1)
    tail = compact[len(num):]
    if tail.startswith(("-", "ـ")):
        return num
    if len(tail) >= 6 and _has_letters(tail):
        return num
    return None


def _has_linked_reference_below(
    page: fitz.Page, clip: fitz.Rect, y: float, tips: dict[str, list[float]] | None
) -> bool:
    if not tips:
        return False
    search_clip = fitz.Rect(clip.x0, y, clip.x1, min(clip.y1, y + 240))
    for block in page.get_text("blocks", clip=search_clip):
        by0 = block[1]
        text = block[4].strip()
        if by0 <= y + 1:
            continue
        num = _reference_marker_number(text)
        if num and any(tip_y < by0 for tip_y in tips.get(num, [])):
            return True
    return False


def _has_footer_text_immediately_below(page: fitz.Page, clip: fitz.Rect, y: float) -> bool:
    search_clip = fitz.Rect(clip.x0, y, clip.x1, min(clip.y1, y + 40))
    blocks = sorted(page.get_text("blocks", clip=search_clip), key=lambda b: b[1])
    for block in blocks:
        by0 = block[1]
        text = re.sub(r"\s+", " ", block[4].strip())
        if not text or by0 <= y + 1:
            continue
        if by0 - y > 25:
            return False
        return bool(
            _reference_marker_number(text)
            or re.match(r'^[\"«]?\s*(طبقا|أنظر|المادة\s+\d+)', text)
        )
    return False


def _is_footer_separator_y(
    page: fitz.Page, clip: fitz.Rect, y: float, tips: dict[str, list[float]] | None
) -> bool:
    if not (clip.y0 < y < clip.y1):
        return False
    if y > (clip.y1 - (clip.height * 0.25)):
        return True
    return (
        _has_footer_text_immediately_below(page, clip, y)
        and _has_linked_reference_below(page, clip, y, tips)
    )


def _collect_superscript_tips(page: fitz.Page, clip: fitz.Rect, body_size: float) -> dict[str, list[float]]:
    """Find all small superscript digits and keep every Y-coordinate per number."""
    # Look at the top 90% of the page to find tips (superscripts)
    body_clip = fitz.Rect(clip.x0, clip.y0, clip.x1, clip.y0 + (clip.height * 0.9))
    data = page.get_text("rawdict", clip=body_clip)
    
    tips: dict[str, list[float]] = {}
    for block in data.get("blocks", []):
        if block.get("type") != 0: continue
        block_spans = [
            span
            for line in block.get("lines", [])
            for span in line.get("spans", [])
        ]
        block_text = "".join(_span_text(span) for span in block_spans)
        block_dominant_size = _dominant_size(block_spans)
        for line in block.get("lines", []):
            line_spans = line.get("spans", [])
            line_text = "".join(_span_text(span) for span in line_spans)
            # Calculate the dominant size in this specific line
            line_dominant_size = _dominant_size(line_spans)
            if not line_dominant_size: continue

            for span in line_spans:
                sz = span.get("size", 0)
                txt = _span_text(span)
                digit_match = "".join(filter(str.isdigit, txt))
                
                if digit_match:
                    # A tip must be a small digit attached to larger nearby text.
                    # This rejects isolated small printed numbers in indexes/tables.
                    is_tip = (
                        (
                            _has_letters(line_text)
                            and sz < line_dominant_size * 0.9
                        )
                        or (
                            _has_letters(block_text)
                            and block_dominant_size
                            and sz < block_dominant_size * 0.9
                        )
                        or (
                            (_has_letters(line_text) or _has_letters(block_text))
                            and sz < body_size * 0.85
                            and sz < 13
                        )
                    )
                        
                    if is_tip:
                        y_bottom = span["bbox"][3]
                        tips.setdefault(digit_match, []).append(y_bottom)
    for ys in tips.values():
        ys.sort()
    return tips


def _detect_footer_by_line(
    page: fitz.Page, 
    clip: fitz.Rect, 
    table_bboxes: list[fitz.Rect] | None = None,
    tips: dict[str, list[float]] | None = None,
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
                        if _is_footer_separator_y(page, clip, y, tips):
                            if best_y is None or y < best_y:
                                best_y = y
            elif item[0] == "re": # rectangle
                rect = item[1]
                if rect.height < 3.0 and rect.width >= min_line_width:
                    y = rect.y0
                    if table_bboxes and any(t.y0 - 2 <= y <= t.y1 + 2 and t.x0 <= rect.x0 + rect.width/2 <= t.x1 for t in table_bboxes):
                        continue
                    if _is_footer_separator_y(page, clip, y, tips):
                        if best_y is None or y < best_y:
                            best_y = y
    return best_y


def _detect_footer_by_text_line(
    page: fitz.Page, clip: fitz.Rect, tips: dict[str, list[float]] | None = None
) -> float | None:
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
                if (
                    _has_footer_text_immediately_below(page, clip, y)
                    and _has_linked_reference_below(page, clip, y, tips)
                ):
                    if best_y is None or y < best_y:
                        best_y = y
    return best_y


def _separator_above_y(
    page: fitz.Page,
    clip: fitz.Rect,
    y_limit: float,
    table_bboxes: list[fitz.Rect] | None = None,
) -> float | None:
    """Find a nearby separator just above a confirmed footer marker."""
    page_width = clip.x1 - clip.x0
    min_line_width = page_width * 0.15
    min_y = clip.y0 + clip.height * 0.45
    max_gap = clip.height * 0.16
    candidates: list[float] = []

    def keep(y: float, x_mid: float) -> None:
        if not (min_y <= y < y_limit and y_limit - y <= max_gap):
            return
        if table_bboxes and any(
            t.y0 - 2 <= y <= t.y1 + 2 and t.x0 <= x_mid <= t.x1
            for t in table_bboxes
        ):
            return
        candidates.append(y)

    for drawing in page.get_drawings():
        for item in drawing.get("items", []):
            if item[0] == "l":
                p1, p2 = item[1], item[2]
                if abs(p1.y - p2.y) < 2.0:
                    width = abs(p1.x - p2.x)
                    if width >= min_line_width:
                        keep(max(p1.y, p2.y), (p1.x + p2.x) / 2)
            elif item[0] == "re":
                rect = item[1]
                if rect.height < 3.0 and rect.width >= min_line_width:
                    keep(rect.y0, rect.x0 + rect.width / 2)

    dict_data = page.get_text("dict", clip=clip)
    for block in dict_data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            if not line.get("spans"):
                continue
            line_text = "".join(span.get("text", "") for span in line["spans"]).strip()
            raw_line_text = "".join(span.get("text", "") for span in line["spans"])
            stripped = line_text.replace(" ", "")
            is_text_line = len(stripped) >= 10 and all(c in "_-ـ." for c in stripped)
            is_space_line = not stripped and len(raw_line_text) >= 30
            if is_text_line or is_space_line:
                bbox = fitz.Rect(line["bbox"])
                keep(bbox.y0, (bbox.x0 + bbox.x1) / 2)

    if not candidates:
        return None
    return max(candidates)


def _detect_footer_by_smart_markers(page, clip: fitz.Rect, tips: dict[str, list[float]]) -> float | None:
    """Strategy 3: Topmost Linked Reference.
    
    Identifies the highest line in the footer area that starts with a number
    matching a superscript tip, ensuring the footer line is physically 
    below the lowest usage of that tip in the body.
    """
    if not tips:
        return None
        
    blocks = page.get_text("blocks", clip=clip)
    latest_match_by_num: dict[str, float] = {}
    
    for b in blocks:
        bx0, by0, bx1, by1, text = b[:5]
        for match in re.finditer(r"^\s*(\d+)", text, flags=re.MULTILINE):
            num = match.group(1)
            # Match per marker number. A reference line is valid if any same-number
            # tip exists above it; keep the latest candidate for that number.
            if any(tip_y < by0 for tip_y in tips.get(num, [])):
                latest_match_by_num[num] = max(by0, latest_match_by_num.get(num, by0))

    if latest_match_by_num:
        # After choosing the latest reference for each number, return the topmost
        # reference among all matched numbers as the footer start candidate.
        return min(latest_match_by_num.values())
        
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
    y = _detect_footer_by_line(page, clip, table_bboxes=table_bboxes, tips=tips_map)
    if y is not None:
        return y, True

    # 3. Text-based Line
    y = _detect_footer_by_text_line(page, clip, tips=tips_map)
    if y is not None:
        return y, True

    # 4. Strategy: Topmost Linked Reference (Using mapped coordinates)
    y = _detect_footer_by_smart_markers(page, clip, tips_map)
    if y is not None:
        separator_y = _separator_above_y(page, clip, y, table_bboxes=table_bboxes)
        if separator_y is not None:
            return separator_y, True
        return y, True

    # 5. Global Font Size Clustering
    y = _detect_footer_by_global_clustering(page, clip, body_size)
    if y is not None:
        return y, False

    return None, False
