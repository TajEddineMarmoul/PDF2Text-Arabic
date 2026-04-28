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
_ARABIC_TOKEN_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]{2,}")
_ARABIC_WORD_RE = re.compile(r"[ء-ي]{2,}")
_ARABIC_RUN_RE = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+"
    r"(?:\s+[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+)+"
)
_LATIN_WORD_RE = re.compile(r"\b[A-Za-z]{4,}\b")
_MIRRORED_PARENS_RE = re.compile(r"\)\s*([^()\n]{1,30}?)\s*\(")
_SWAPPED_GUILLEMETS_RE = re.compile(r"»\s*([^«»\n]{1,120}?)\s*«")
_DCI_VARIANTS_RE = re.compile(r"(?<!\S)(?:م\s+د\s+ت|ت\s+د\s+م)(?!\S)")
_DUPLICATE_ARABIC_LINE_RE = re.compile(r"(?m)^[ \t]*([ء-ي]{2,})(?:[ \t]+\1)+[ \t]*$")
_JOINED_DEMO_ARTICLE_RE = re.compile(
    r"\b((?:هذا|هذه|ذلك|تلك|لهذا|لهذه|بهذا|بهذه|وفيهذا|وفيهذه))(?:ال|لا)([ء-ي]{2,})\b"
)
_JOINED_PRONOUN_ARTICLE_RE = re.compile(
    r"\b([ء-ي]{3,}(?:ها|هم|هن|ه|ك|ي|نا|هما))(?:ال|لا)([ء-ي]{2,})\b"
)
_JOINED_SHORT_PRONOUN_ARTICLE_RE = re.compile(
    r"\b((?:(?:في|ب|ل|من|عن|على|إلى)?(?:ها|هم|هن|ه|ك|ي|نا|هما)))(?:ال|لا)([ء-ي]{2,})\b"
)
_OCR_WORD_FIXES = {
    "إعالم": "إعلام",
    "الإعالم": "الإعلام",
    "والإعالم": "والإعلام",
    "بإعالم": "بإعلام",
    "بالإعالم": "بالإعلام",
    "والتصال": "والاتصال",
    "لألشخاص": "للأشخاص",
    "واستغاللها": "واستغلالها",
    "استهالك": "استهلاك",
    "الاستهالك": "الاستهلاك",
    "الالزمة": "اللازمة",
    "الامسلحة": "المسلحة",
    "الاعسكري": "العسكري",
    "الاوطنية": "الوطنية",
    "وكذالاتزاماتهم": "وكذا التزاماتهم",
    "الامتخذة": "المتخذة",
    "مقاوالت": "مقاولات",
    "ومقاوالت": "ومقاولات",
    "بمقاوالت": "بمقاولات",
    "المقاوالت": "المقاولات",
    "والمقاوالت": "والمقاولات",
    "مالئمة": "ملائمة",
    "ومالئمة": "وملائمة",
    "المالئمة": "الملائمة",
    "صالبة": "صلبة",
    "إلعادة": "لإعادة",
    "والمالقات": "والملحقات",
    "والتهييئات": "والتهيئات",
    "مالءمة": "ملاءمة",
    "ومالءمة": "وملاءمة",
}

_OCR_WORD_FIXES.update(
    {
        "استغالل": "استغلال",
        "واستغالل": "واستغلال",
        "مبادالت": "مبادلات",
        "والمبادالت": "والمبادلات",
        "تسهيالت": "تسهيلات",
        "التسهيالت": "التسهيلات",
        "القتراح": "لاقتراح",
        "إدالء": "إدلاء",
        "الإدالء": "الإدلاء",
        "إخالال": "إخلالا",
        "اجراءات": "إجراءات",
        "الاجراءات": "الإجراءات",
        "والاجراءات": "والإجراءات",
        "هؤالء": "هؤلاء",
        "تبادلهالا": "تبادلها لا",
        "إال": "إلا",
        "إلذن": "لإذن",
        "المجاالت": "المجالات",
        "مجاالت": "مجالات",
        "والهيأت": "والهيئات",
        "الهيأت": "الهيئات",
        "مالم": "ما لم",
        "حاصال": "حاصلا",
        "الحاصالت": "الحاصلات",
        "خالل": "خلال",
        "وخالل": "وخلال",
        "الإخالل": "الإخلال",
        "لإلخالل": "للإخلال",
    }
)

# Arabic letters that do NOT join to the next letter
_NON_JOINING_FORWARD = set("اأإآدذرزوؤةىء\u0671")
_UNLIKELY_ARABIC_START = set("ةى")
_STRIP_ARABIC_TOKEN = "\"'`~!@#$%^&*()-_=+[{]}\\|;:,<.>/?؟؛،«»“”\n\r\t "

# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def looks_like_scrambled_arabic(text: str) -> bool:
    """Return True when selectable Arabic is likely stored backwards.

    The strongest signal is reversed definite-article words: normal Arabic
    commonly starts words with ``ال``; scrambled extraction often turns that
    into a word ending in ``لا``.
    """
    long_tokens = _arabic_long_tokens(text)
    if not long_tokens:
        return False

    start_al = sum(1 for t in long_tokens if t.startswith("ال"))
    end_la = sum(1 for t in long_tokens if t.endswith("لا"))
    unlikely = sum(1 for t in long_tokens if t[0] in _UNLIKELY_ARABIC_START)
    count = len(long_tokens)

    start_al_ratio = start_al / count
    end_la_ratio = end_la / count
    unlikely_ratio = unlikely / count

    if count >= 15 and end_la_ratio >= 0.25 and start_al_ratio <= 0.05:
        return True
    if count >= 10 and unlikely_ratio >= 0.15:
        return True
    if count >= 20 and unlikely_ratio >= 0.10:
        return True

    return _has_scrambled_arabic_line(text)


def clean_arabic(text: str) -> str:
    """Post-process extracted text: normalize, strip invisibles, fix spacing."""
    # Map common PUA bullet points
    text = text.replace("\uf02d", "-")
    
    # GLOBAL LIGATURE CORRECTOR: Fix common 'Lam-Alef' decomposition artifacts
    # Handles cases like 'اإل' -> 'الإ', 'اال' -> 'الا', and 'ا ا ل' (space jitter)
    # Pattern: Alef + optional space + Alef variant + optional space + Lam.
    # Restrict to token starts so "جسيما الاجراءات" is not merged into one word.
    text = re.sub(
        r"(?<![ء-ي])([وفبكل])ا\s*([\u0622\u0623\u0625\u0627])\s*ل(?=[ء-ي])",
        r"\1ال\2",
        text,
    )
    text = re.sub(r"(?<![ء-ي])ا\s*([\u0622\u0623\u0625\u0627])\s*ل", r"ال\1", text)
    
    text = unicodedata.normalize("NFKC", text)
    text = _ZW_RE.sub("", text)
    text = text.replace("\u0640", "")
    text = _repair_lam_alef_ocr_swaps(text)
    text = _repair_reversed_latin_words(text)
    text = _MIRRORED_PARENS_RE.sub(_repair_mirrored_parentheses, text)
    text = _SWAPPED_GUILLEMETS_RE.sub(r"«\1»", text)
    text = _repair_scrambled_arabic_runs(text)
    text = _JOINED_DEMO_ARTICLE_RE.sub(r"\1 ال\2", text)
    text = _JOINED_SHORT_PRONOUN_ARTICLE_RE.sub(r"\1 ال\2", text)
    text = _JOINED_PRONOUN_ARTICLE_RE.sub(r"\1 ال\2", text)
    text = _apply_ocr_word_fixes(text)
    text = _ARABIC_DIGIT_RE.sub(r"\1 \2", text)
    text = _DIGIT_ARABIC_RE.sub(r"\1 \2", text)
    text = _SPACES_RE.sub(" ", text)
    text = _DCI_VARIANTS_RE.sub("م-د-ت", text)
    text = _NEWLINES_RE.sub("\n\n", text)
    return text


def _repair_lam_alef_ocr_swaps(text: str) -> str:
    """Repair recurring OCR swaps where ``لا`` is emitted as ``ال``."""
    text = _DUPLICATE_ARABIC_LINE_RE.sub(r"\1", text)
    text = re.sub(r"(?<![ء-ي])لاليفاء(?![ء-ي])", "للإيفاء", text)
    text = re.sub(r"(?<![ء-ي])لالتفاقية(?![ء-ي])", "للاتفاقية", text)
    text = re.sub(r"(?<![ء-ي])المتحانات(?=\s+الحصول)", "لامتحانات", text)
    text = re.sub(r"(?<![ء-ي])اختالف([ء-ي]*)(?![ء-ي])", r"اختلاف\1", text)
    text = text.replace("عالوة", "علاوة")

    def repair_token(match: re.Match[str]) -> str:
        token = match.group(0)
        if token.endswith("الت"):
            prefix = token[:-3]
            if len(prefix) >= 2 or prefix == "آ":
                return f"{prefix}لات"
        return token

    return _ARABIC_WORD_RE.sub(repair_token, text)


def _arabic_long_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for token in _ARABIC_TOKEN_RE.findall(text):
        token = token.strip(_STRIP_ARABIC_TOKEN)
        if len(token) < 4:
            continue
        letters = sum(1 for ch in token if is_arabic(ch))
        if letters >= max(2, int(0.6 * len(token))):
            tokens.append(token)
    return tokens


def _has_scrambled_arabic_line(text: str) -> bool:
    for line in text.splitlines():
        tokens = _arabic_long_tokens(line)
        if len(tokens) < 3:
            continue
        bad = [t for t in tokens if t[0] in _UNLIKELY_ARABIC_START]
        has_latin = any(ch.isalpha() and not is_arabic(ch) for ch in line)
        if len(bad) >= 3:
            return True
        if has_latin and len(bad) >= 2:
            return True
    return False


def _is_scrambled_arabic_run(text: str) -> bool:
    tokens = [
        token.strip(_STRIP_ARABIC_TOKEN)
        for token in _ARABIC_TOKEN_RE.findall(text)
        if len(token.strip(_STRIP_ARABIC_TOKEN)) >= 3
    ]
    if len(tokens) < 2:
        return False

    count = len(tokens)
    start_al = sum(1 for t in tokens if t.startswith("ال")) / count
    end_la = sum(1 for t in tokens if t.endswith("لا")) / count
    unlikely = sum(1 for t in tokens if t[0] in _UNLIKELY_ARABIC_START) / count

    if count == 2:
        return end_la >= 0.50 and start_al == 0.0

    return (end_la >= 0.25 and start_al <= 0.10) or unlikely >= 0.60


def _repair_scrambled_arabic_runs(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        run = match.group(0)
        if not _is_scrambled_arabic_run(run):
            return run
        tokens = run.split()
        return " ".join(token[::-1] for token in reversed(tokens))

    return _ARABIC_RUN_RE.sub(repl, text)


def _repair_reversed_latin_words(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        token = match.group(0)
        candidate = token[::-1]
        if (
            candidate[0].isupper()
            and candidate[1:].islower()
            and (token[-1].isupper() or token[0].islower())
        ):
            return candidate
        return token

    return _LATIN_WORD_RE.sub(repl, text)


def _repair_mirrored_parentheses(match: re.Match[str]) -> str:
    content = match.group(1).strip()
    if content == "ICD":
        content = "DCI"
    return f"({content})"


def _apply_ocr_word_fixes(text: str) -> str:
    text = re.sub(r"(?<![ء-ي])إصالح([ء-ي]*)(?![ء-ي])", r"إصلاح\1", text)
    text = text.replace("إدالء", "إدلاء")
    text = text.replace("حاصال", "حاصلا")
    text = text.replace("خالل", "خلال")
    text = text.replace("إخالل", "إخلال")
    text = text.replace("لإلخلال", "للإخلال")
    text = re.sub(r"(?<![ء-ي])لأل([ء-ي]+)(?![ء-ي])", r"للأ\1", text)
    for bad, good in _OCR_WORD_FIXES.items():
        text = re.sub(
            rf"(?<![ء-ي]){re.escape(bad)}(?![ء-ي])",
            good,
            text,
        )
    text = re.sub(r"(?<![ء-ي])ال(?![ء-ي])", "لا", text)
    return text

def merge_lines_by_y(lines: list[dict]) -> list[dict]:
    """Merge rawdict lines that share the same vertical position into rows."""
    if not lines:
        return []

    rows: list[dict] = []
    for line in lines:
        cy = (line["bbox"][1] + line["bbox"][3]) / 2
        h = line["bbox"][3] - line["bbox"][1]
        # Use a consistent 3px tolerance for row merging
        tolerance = 3.0

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
    """Build text from merged spans by spatial analysis."""
    all_chars: list[dict] = []
    for span in spans:
        all_chars.extend(span.get("chars", []))
    
    if not all_chars:
        return ""
        
    all_chars = fix_zero_width_clusters(all_chars)

    # Heuristic for RTL: compare Arabic letters vs Latin letters
    arabic_count = sum(1 for c in all_chars if is_arabic(c["c"]))
    latin_count = sum(1 for c in all_chars if c["c"].isalpha() and not is_arabic(c["c"]))
    is_rtl = arabic_count >= latin_count

    # STABILIZED SORTING: Use Proximity Clustering for vertical grouping
    # This prevents minor Y-jitter from flipping letters.
    all_chars.sort(key=lambda c: c["bbox"][1]) # Sort by Y
    rows = []
    if all_chars:
        current_row = [all_chars[0]]
        for i in range(1, len(all_chars)):
            c = all_chars[i]
            # If char is within 3px of any char in the current row, it's the same line
            if abs(c["bbox"][1] - current_row[-1]["bbox"][1]) < 3.0:
                current_row.append(c)
            else:
                rows.append(current_row)
                current_row = [c]
        rows.append(current_row)

    # Sort each row horizontally
    sorted_chars = []
    for row in rows:
        if is_rtl:
            # RTL: largest X first (right to left).
            # We use a 1.0px snap to handle horizontal jitter in tables.
            row.sort(key=lambda c: (-round(c["bbox"][0]), -c["bbox"][1]))
        else:
            # LTR: smallest X first (left to right)
            row.sort(key=lambda c: (round(c["bbox"][0]), c["bbox"][1]))
        sorted_chars.extend(row)

    widths = [c["bbox"][2] - c["bbox"][0] for c in sorted_chars if (c["bbox"][2] - c["bbox"][0]) > 0.5]
    avg_width = median(widths) if widths else 6.0
    space_threshold = avg_width * 0.6

    parts: list[str] = []
    prev_x0 = None
    prev_x1 = None
    prev_c = None
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
            
            # Connection check
            if (prev_c is not None and is_arabic(prev_c) and prev_c not in _NON_JOINING_FORWARD and is_arabic(c)):
                threshold = space_threshold * 3.0
            else:
                threshold = space_threshold
                
            if gap > threshold or (had_space and gap > 0.5):
                parts.append(" ")
            had_space = False

        if is_rtl and (c.isdigit() or c in ".,-/"):
            ltr_run = []
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
            prev_x0, prev_x1, prev_c = last["bbox"][0], last["bbox"][2], last["c"]
            i = j
        else:
            parts.append(c)
            prev_x0, prev_x1, prev_c = x0, x1, c
            i += 1

    return "".join(parts)
