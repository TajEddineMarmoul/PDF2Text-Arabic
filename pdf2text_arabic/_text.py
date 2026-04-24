"""Text building, cleaning, and line merging utilities.

Handles RTL/LTR character sorting, spatial gap-based space insertion,
digit-run reversal, NFKC normalization, and y-coordinate line merging.
"""

import re
import unicodedata
from statistics import median

from ._chars import fix_zero_width_clusters, is_arabic

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ZW_RE = re.compile(r"[\u200b\u200c\u200d\ufeff\u200e\u200f]")
_ARABIC_DIGIT_RE = re.compile(r"([\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF])(\d)")
_DIGIT_ARABIC_RE = re.compile(r"(\d)([\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF])")
_SPACES_RE = re.compile(r"[ \t]+")
_NEWLINES_RE = re.compile(r"\n{3,}")

# Arabic letters that do NOT join to the next letter (their final/isolated
# form is the same regardless of what follows).  Any gap after these letters
# is naturally present and common inside words; any gap after a letter NOT in
# this set is suspicious because the letters should visually connect.
_NON_JOINING_FORWARD = set("اأإآدذرزوؤةىء\u0671")

# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def clean_arabic(text: str) -> str:
    """Post-process extracted text: normalize, strip invisibles, fix spacing."""
    text = unicodedata.normalize("NFKC", text)
    text = _ZW_RE.sub("", text)
    text = text.replace("\u0640", "")
    text = _ARABIC_DIGIT_RE.sub(r"\1 \2", text)
    text = _DIGIT_ARABIC_RE.sub(r"\1 \2", text)
    text = _SPACES_RE.sub(" ", text)
    text = _NEWLINES_RE.sub("\n\n", text)
    return text


def merge_lines_by_y(lines: list[dict]) -> list[dict]:
    """Merge rawdict lines that share the same vertical position into rows.

    PyMuPDF frequently splits one visual text row into multiple rawdict
    "lines" at the same y-coordinate.  This merges them back together.
    """
    if not lines:
        return []

    rows: list[dict] = []
    for line in lines:
        cy = (line["bbox"][1] + line["bbox"][3]) / 2
        h = line["bbox"][3] - line["bbox"][1]
        tolerance = max(2.0, h * 0.3)

        merged = False
        for row in rows:
            if abs(cy - row["cy"]) <= tolerance:
                row["spans"].extend(line["spans"])
                n = row["count"]
                row["cy"] = (row["cy"] * n + cy) / (n + 1)
                row["count"] = n + 1
                merged = True
                break

        if not merged:
            rows.append({"cy": cy, "count": 1, "spans": list(line["spans"])})

    return rows


def build_row_text(spans: list[dict]) -> str:
    """Build text from merged spans by spatial analysis.

    Chars are sorted by x-position (descending for RTL, ascending for LTR).
    Spaces are inserted where spatial gaps exceed a threshold.  LTR digit
    runs within RTL text are detected and reversed to restore correct order.
    """
    all_chars: list[dict] = []
    for span in spans:
        all_chars.extend(span.get("chars", []))
    all_chars = fix_zero_width_clusters(all_chars)

    if not all_chars:
        return ""

    # Heuristic for RTL: compare Arabic letters vs Latin letters.
    # We ignore digits, symbols, and punctuation when deciding the base text direction
    # because digits can appear in both RTL and LTR contexts and shouldn't flip the line.
    arabic_count = sum(1 for c in all_chars if is_arabic(c["c"]))
    latin_count = sum(1 for c in all_chars if c["c"].isalpha() and not is_arabic(c["c"]))

    # Default to RTL in this Arabic-first tool unless Latin letters strictly outnumber Arabic ones
    is_rtl = arabic_count >= latin_count
    if is_rtl:
        sorted_chars = sorted(all_chars, key=lambda c: -c["bbox"][0])
    else:
        sorted_chars = sorted(all_chars, key=lambda c: c["bbox"][0])

    widths = [
        c["bbox"][2] - c["bbox"][0]
        for c in sorted_chars
        if (c["bbox"][2] - c["bbox"][0]) > 0.5
    ]
    avg_width = median(widths) if widths else 6.0
    space_threshold = avg_width * 0.6

    parts: list[str] = []
    prev_x0: float | None = None
    prev_x1: float | None = None
    prev_c: str | None = None
    had_space = False

    i = 0
    while i < len(sorted_chars):
        ch = sorted_chars[i]
        c = ch["c"]
        x0, x1 = ch["bbox"][0], ch["bbox"][2]

        if c.strip() == "":
            had_space = True
            i += 1
            continue

        if prev_x0 is not None and prev_x1 is not None:
            if is_rtl:
                gap = prev_x0 - x1
            else:
                gap = x0 - prev_x1
            # If the previous Arabic letter joins forward to this Arabic
            # letter, they belong to the same word — require a much larger
            # gap to split them (kashida-stretched connections can otherwise
            # be wider than space_threshold).
            if (
                prev_c is not None
                and is_arabic(prev_c)
                and prev_c not in _NON_JOINING_FORWARD
                and is_arabic(c)
            ):
                threshold = space_threshold * 3.0
            else:
                threshold = space_threshold
            if gap > threshold or (had_space and gap > 0.5):
                parts.append(" ")
            had_space = False

        if is_rtl and (c.isdigit() or c in ".,-/"):
            ltr_run: list[str] = []
            j = i
            while j < len(sorted_chars):
                sc = sorted_chars[j]["c"]
                if sc.isdigit() or sc in ".,-/":
                    ltr_run.append(sc)
                    j += 1
                else:
                    break
            ltr_run.reverse()
            parts.append("".join(ltr_run))
            last = sorted_chars[j - 1]
            prev_x0 = last["bbox"][0]
            prev_x1 = last["bbox"][2]
            prev_c = last["c"]
            i = j
        else:
            parts.append(c)
            prev_x0 = x0
            prev_x1 = x1
            prev_c = c
            i += 1

    return "".join(parts)
