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

from ._text import build_row_text, clean_arabic, merge_lines_by_y

_HEADING_SIZE_MIN = 20
_EXPERIMENTAL_FONT_BACKTRACK = True

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


def _collect_superscript_tips(
    page: fitz.Page,
    clip: fitz.Rect,
    body_size: float,
    raw_data: dict | None = None,
) -> dict[str, list[float]]:
    """Find all small superscript digits and keep every Y-coordinate per number."""
    # Look at the top 95% of the page to find tips (superscripts)
    body_clip = fitz.Rect(clip.x0, clip.y0, clip.x1, clip.y0 + (clip.height * 0.95))
    data = raw_data if raw_data is not None else page.get_text("rawdict", clip=body_clip)
    
    tips: dict[str, list[float]] = {}
    for block in data.get("blocks", []):
        if block.get("type") != 0: continue
        block_spans = [
            span
            for line in block.get("lines", [])
            if line.get("bbox", [0, 0, 0, 0])[1] < body_clip.y1
            for span in line.get("spans", [])
        ]
        block_text = "".join(_span_text(span) for span in block_spans)
        block_dominant_size = _dominant_size(block_spans)
        for line in block.get("lines", []):
            if line.get("bbox", [0, 0, 0, 0])[1] >= body_clip.y1:
                continue
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
                    )

                    if is_tip:
                        # A real superscript is a LONE small digit. Reject when
                        # the candidate is part of a hierarchical numbering
                        # pattern (e.g. "3-7-1", "2-", "1.2.3"): either another
                        # small digit of the same font/size or a dash/dot-only
                        # separator sits within ~30px in the same block.
                        sx0, sy0, sx1, sy1 = span.get("bbox", [0, 0, 0, 0])
                        span_font = span.get("font")
                        for other in block_spans:
                            if other is span:
                                continue
                            other_txt = _span_text(other)
                            if not other_txt:
                                continue
                            is_sibling_digit = (
                                any(c.isdigit() for c in other_txt)
                                and other.get("font") == span_font
                                and abs(other.get("size", 0) - sz) < 0.5
                            )
                            is_separator = all(
                                c in "-‐‑‒–—./" for c in other_txt
                            )
                            if not (is_sibling_digit or is_separator):
                                continue
                            ox0, oy0, ox1, oy1 = other.get("bbox", [0, 0, 0, 0])
                            dx = max(0.0, max(sx0, ox0) - min(sx1, ox1))
                            dy = max(0.0, max(sy0, oy0) - min(sy1, oy1))
                            if dx <= 30 and dy <= 30:
                                is_tip = False
                                break

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
    drawings: list[dict] | None = None,
) -> float | None:
    """Strategy 1: Detect horizontal separator line."""
    page_width = clip.x1 - clip.x0
    min_line_width = page_width * 0.15

    drawings = drawings if drawings is not None else page.get_drawings()
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
    page: fitz.Page,
    clip: fitz.Rect,
    tips: dict[str, list[float]] | None = None,
    dict_data: dict | None = None,
) -> float | None:
    """Strategy 2: Detect text-based separator lines (e.g. '---', '___')."""
    dict_data = dict_data if dict_data is not None else page.get_text("dict", clip=clip)
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
    drawings: list[dict] | None = None,
    dict_data: dict | None = None,
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

    drawings = drawings if drawings is not None else page.get_drawings()
    for drawing in drawings:
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

    dict_data = dict_data if dict_data is not None else page.get_text("dict", clip=clip)
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


def _confirmed_footer_blocks(
    page: fitz.Page,
    clip: fitz.Rect,
    tips: dict[str, list[float]],
) -> list[dict]:
    """Return the latest confirmed footer block for each superscript number."""
    latest_by_num: dict[str, dict] = {}
    for block in page.get_text("blocks", clip=clip):
        bx0, by0, bx1, by1, text = block[:5]
        for match in re.finditer(r"^\s*(\d+)", text, flags=re.MULTILINE):
            num = match.group(1)
            if any(tip_y < by0 for tip_y in tips.get(num, [])):
                previous = latest_by_num.get(num)
                if previous is None or by0 > previous["y0"]:
                    latest_by_num[num] = {
                        "num": num,
                        "bbox": fitz.Rect(bx0, by0, bx1, by1),
                        "text": text,
                        "y0": by0,
                        "y1": by1,
                    }
                break
    return list(latest_by_num.values())


def _font_family(font_name: str) -> str:
    """Normalize subset/style font names like ABCDEF+FontName,Bold."""
    name = font_name.split("+")[-1]
    return re.split(r"[, -](?:Bold|Italic|Oblique|Regular|Normal|Medium|Light|Black)", name, maxsplit=1, flags=re.I)[0]


def _font_style(font_name: str) -> str:
    name = font_name.lower()
    is_bold = any(token in name for token in ("bold", "black", "heavy", "semibold"))
    is_italic = any(token in name for token in ("italic", "oblique"))
    if is_bold and is_italic:
        return "bold-italic"
    if is_bold:
        return "bold"
    if is_italic:
        return "italic"
    return "normal"


def _span_font_profile(span: dict) -> tuple[str, str, float]:
    return (
        _font_family(span.get("font", "")),
        _font_style(span.get("font", "")),
        round(float(span.get("size", 0)), 1),
    )


def _row_y0(row: dict) -> float:
    return min(span["bbox"][1] for span in row["spans"])


def _row_y1(row: dict) -> float:
    return max(span["bbox"][3] for span in row["spans"])


def _row_text(row: dict) -> str:
    return clean_arabic(build_row_text(row["spans"])).strip()


def _row_font_profile(row: dict) -> tuple[str, str, float] | None:
    font_chars: dict[tuple[str, str, float], int] = {}
    for span in row["spans"]:
        text = _span_text(span)
        if not text:
            continue
        key = _span_font_profile(span)
        font_chars[key] = font_chars.get(key, 0) + len(text)
    if not font_chars:
        return None
    return max(font_chars.items(), key=lambda item: item[1])[0]


def _row_font_profiles(row: dict) -> set[tuple[str, str, float]]:
    return {
        _span_font_profile(span)
        for span in row["spans"]
        if _span_text(span)
    }


def _row_in_table(row: dict, table_bboxes: list[fitz.Rect] | None) -> bool:
    if not table_bboxes:
        return False
    y0 = _row_y0(row)
    y1 = _row_y1(row)
    x0 = min(span["bbox"][0] for span in row["spans"])
    x1 = max(span["bbox"][2] for span in row["spans"])
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    return any(t.x0 <= cx <= t.x1 and t.y0 - 2 <= cy <= t.y1 + 2 for t in table_bboxes)


def _font_backtrack_above_y(
    page: fitz.Page,
    clip: fitz.Rect,
    y_limit: float,
    tips: dict[str, list[float]],
    table_bboxes: list[fitz.Rect] | None = None,
) -> float | None:
    """Experimental footer expansion by adjacent same-font rows.

    First records font profiles used in the initially detected footer area,
    then walks upward through nearby rows that use one of those profiles.
    """
    raw_data = page.get_text("rawdict", clip=clip)
    confirmed_blocks = _confirmed_footer_blocks(page, clip, tips)
    if not confirmed_blocks:
        return None

    rows: list[dict] = []
    for block in raw_data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for row in merge_lines_by_y(block.get("lines", [])):
            if not row.get("spans") or _row_in_table(row, table_bboxes):
                continue
            text = _row_text(row)
            profile = _row_font_profile(row)
            if not text or profile is None:
                continue
            rows.append({
                "row": row,
                "text": text,
                "profile": profile,
                "profiles": _row_font_profiles(row),
                "y0": _row_y0(row),
                "y1": _row_y1(row),
            })

    if not rows:
        return None

    rows.sort(key=lambda item: item["y0"])

    start_y = min(block["y0"] for block in confirmed_blocks)
    start_index = None
    for i, item in enumerate(rows):
        if item["y0"] >= start_y - 2:
            start_index = i
            break

    if start_index is None:
        return None

    footer_profiles: set[tuple[str, str, float]] = set()
    for item in rows[start_index:]:
        footer_profiles.update(item["profiles"])

    if not footer_profiles:
        return None

    heights = [item["y1"] - item["y0"] for item in rows if item["y1"] > item["y0"]]
    heights.sort()
    median_height = heights[len(heights) // 2] if heights else 7.0
    max_gap = max(18.0, median_height * 2.5)

    start = rows[start_index]
    best_y = start["y0"]
    current = start

    for previous in reversed(rows[:start_index]):
        gap = current["y0"] - previous["y1"]
        if gap > max_gap:
            break
        if not (previous["profiles"] & footer_profiles):
            break
        best_y = previous["y0"]
        current = previous

    # This helper is only allowed to expand the footer upward.  If the row-level
    # start is below the block-level smart marker, keep the original smart cut.
    if best_y >= y_limit - 1:
        return None

    separator_y = _separator_above_y(page, clip, start["y0"], table_bboxes=table_bboxes)
    if separator_y is not None and 0 <= best_y - separator_y <= 20:
        return separator_y
    return best_y


def _detect_footer_by_smart_markers(page, clip: fitz.Rect, tips: dict[str, list[float]]) -> float | None:
    """Strategy 3: Topmost Linked Reference.
    
    Identifies the highest line in the footer area that starts with a number
    matching a superscript tip, ensuring the footer line is physically 
    below the lowest usage of that tip in the body.
    """
    if not tips:
        return None

    confirmed_blocks = _confirmed_footer_blocks(page, clip, tips)
    if confirmed_blocks:
        # After choosing the latest reference for each number, return the topmost
        # reference among all matched numbers as the footer start candidate.
        return min(block["y0"] for block in confirmed_blocks)
        
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
        if _EXPERIMENTAL_FONT_BACKTRACK:
            font_y = _font_backtrack_above_y(
                page,
                clip,
                y,
                tips_map,
                table_bboxes=table_bboxes,
            )
            if font_y is not None:
                if separator_y is not None:
                    return min(separator_y, font_y), True
                return font_y, True

        if separator_y is not None:
            return separator_y, True
        return y, True

    # 5. Global Font Size Clustering
    y = _detect_footer_by_global_clustering(page, clip, body_size)
    if y is not None:
        return y, False

    return None, False
