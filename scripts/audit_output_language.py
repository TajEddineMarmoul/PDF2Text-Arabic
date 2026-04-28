"""
Audit extracted page text under output/all_pages for Arabic language quality issues.

This is a heuristic audit (no ground-truth). It flags pages that are very likely
corrupted (full RTL reversal, reversed Latin tokens, mirrored parentheses, etc.)
and produces a Markdown report with concrete examples.

Usage (PowerShell):
  python scripts/audit_output_language.py

Optional:
  python scripts/audit_output_language.py --input-dir output/all_pages --out-md output/reports/audit.md
"""

from __future__ import annotations

import argparse
import datetime as _dt
import glob
import os
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass


ARABIC_BLOCKS = [
    (0x0600, 0x06FF),
    (0x0750, 0x077F),
    (0x08A0, 0x08FF),
    # NOTE: intentionally excluding presentation forms; those are checked separately.
]


def _is_arabic_cp(cp: int) -> bool:
    return any(a <= cp <= b for a, b in ARABIC_BLOCKS)


def _is_arabic_letter(ch: str) -> bool:
    cp = ord(ch)
    return _is_arabic_cp(cp) and unicodedata.category(ch).startswith("L")


def _is_latin_letter(ch: str) -> bool:
    cp = ord(ch)
    return (0x0041 <= cp <= 0x005A) or (0x0061 <= cp <= 0x007A)


_AR_TOKEN_PAT = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]{2,}")
_STRIP_PUNCT = "\"'`~!@#$%^&*()-_=+[{]}\\|;:,<.>/?؟؛،«»“”\n\r\t "

# Full RTL reversal: Arabic words extracted as character-reversed due to bad PDF text encoding.
# A strong signal is that many long tokens end with "لا" (reversed "ال") and almost none start with "ال".
_DEF_ARTICLE_PREFIX = "ال"
_DEF_ARTICLE_SUFFIX_WHEN_REVERSED = "لا"
_UNLIKELY_AR_START = set("ةى")

# Spaced-out letters: "ا ت د م ا"
_SPACED_LETTERS_PAT = re.compile(r"(?:[\u0600-\u06FF]\s){4,}[\u0600-\u06FF]")

# Reversed Latin tokens: potS, enicaxolfixoM, LixoviP, etc.
_REV_LAT_1 = re.compile(r"\b[a-z]{2,}[A-Z]{1,2}\b")
_REV_LAT_2 = re.compile(r"\b[A-Z][a-z]{2,}[A-Z]{1,2}\b")

# Mirrored parentheses: )1977(, )potS(, )DCI(
_MIRRORED_PARENS_PAT = re.compile(r"\)\s*[^\s\n]{1,30}\s*\(")

# Swapped guillemets: » ... « on the same line
_SWAPPED_GUILLEMET_PAT = re.compile(r"»[^\n]{1,120}«")

# Numeric artifacts
_LEADING_ZERO_NUM_PAT = re.compile(r"\b0{2,}\d+(?:[.,]\d+){1,}\b")
_LONG_NUM_RUN_PAT = re.compile(r"\b[0-9][0-9\.,]{17,}[0-9]\b")


@dataclass(frozen=True)
class PageAudit:
    path: str
    doc: str
    words: int
    nonempty_lines: int
    words_per_line: float
    arabic_letters: int
    latin_letters: int

    # Reversal signals
    long_ar_tokens: int
    start_al_ratio: float
    end_la_ratio: float
    unlikely_start_ratio: float
    full_rtl_reversal: bool
    partial_rtl_corruption: bool

    # Other issues
    spaced_letters: bool
    reversed_latin: bool
    reversed_latin_tokens: list[str]
    mirrored_parens: bool
    swapped_guillemets: bool
    leading_zero_numbers: list[str]
    long_numeric_runs: list[str]
    many_double_quotes: bool
    quote_count: int
    fragmented_lines: bool


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _file_head(path: str, n: int = 10) -> str:
    out: list[str] = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for _ in range(n):
            ln = f.readline()
            if not ln:
                break
            out.append(ln.rstrip("\n"))
    return "\n".join(out)


def _compute_reversal_flags(text: str) -> tuple[int, float, float, float, bool, bool]:
    """
    Returns:
      long_count, start_al_ratio, end_la_ratio, unlikely_start_ratio, full, partial
    """
    raw_tokens = _AR_TOKEN_PAT.findall(text)
    tokens: list[str] = []
    for t in raw_tokens:
        t = t.strip(_STRIP_PUNCT)
        if len(t) < 2:
            continue
        letters = sum(1 for ch in t if _is_arabic_letter(ch))
        if letters < max(2, int(0.6 * len(t))):
            continue
        tokens.append(t)

    long_tokens = [t for t in tokens if len(t) >= 4]
    n = len(long_tokens)
    if n == 0:
        return 0, 0.0, 0.0, 0.0, False, False

    start_al = sum(1 for t in long_tokens if t.startswith(_DEF_ARTICLE_PREFIX))
    end_la = sum(1 for t in long_tokens if t.endswith(_DEF_ARTICLE_SUFFIX_WHEN_REVERSED))
    unlikely = sum(1 for t in long_tokens if t and t[0] in _UNLIKELY_AR_START)

    start_al_ratio = start_al / n
    end_la_ratio = end_la / n
    unlikely_ratio = unlikely / n

    # Full reversal is extremely strong and consistent: almost no "ال" at the start,
    # but tons of "لا" at the end.
    full = (
        (n >= 15 and end_la_ratio >= 0.25 and start_al_ratio <= 0.05)
        or (n >= 10 and unlikely_ratio >= 0.15)
        or (n >= 20 and unlikely_ratio >= 0.10)
    )

    # Partial corruption: a few reversed tokens inside an otherwise readable page.
    # We keep this conservative.
    partial = (not full) and (unlikely_ratio >= 0.03 and unlikely >= 2)

    return n, start_al_ratio, end_la_ratio, unlikely_ratio, full, partial


def audit_page(txt_path: str) -> PageAudit:
    text = _read_text(txt_path)

    doc = os.path.basename(os.path.dirname(txt_path))
    rel = txt_path.replace("\\", "/")

    lines = [ln for ln in text.splitlines() if ln.strip()]
    words = text.split()
    wpl = (len(words) / len(lines)) if lines else 0.0

    arabic_letters = sum(1 for ch in text if _is_arabic_letter(ch))
    latin_letters = sum(1 for ch in text if _is_latin_letter(ch))

    long_n, start_al_ratio, end_la_ratio, unlikely_ratio, full_rev, partial_rev = _compute_reversal_flags(
        text
    )

    # Refine partial reversal: require >=3 suspicious-start tokens on a single line
    # OR >=2 suspicious-start tokens in a mixed-script line.
    if partial_rev:
        pat_tok = re.compile(r"[\u0600-\u06FF]{3,}")
        found_line = False
        for ln in text.splitlines():
            toks = [t for t in pat_tok.findall(ln) if len(t) >= 4]
            bad = [t for t in toks if t and t[0] in _UNLIKELY_AR_START]
            if len(bad) >= 3:
                found_line = True
                break
            if len(bad) >= 2 and any(_is_latin_letter(ch) for ch in ln):
                found_line = True
                break
        partial_rev = found_line

    spaced = bool(_SPACED_LETTERS_PAT.search(text))
    rev_lat_tokens = sorted(set(_REV_LAT_1.findall(text) + _REV_LAT_2.findall(text)))
    rev_lat = bool(rev_lat_tokens)

    mirrored_parens = bool(_MIRRORED_PARENS_PAT.search(text))
    swapped_guil = bool(_SWAPPED_GUILLEMET_PAT.search(text))

    leading_zero_nums = sorted(set(_LEADING_ZERO_NUM_PAT.findall(text)))
    long_num_runs = sorted(set(_LONG_NUM_RUN_PAT.findall(text)))

    quote_count = text.count("\"")
    many_quotes = quote_count >= 50

    fragmented = len(words) >= 50 and wpl < 4.0

    return PageAudit(
        path=rel,
        doc=doc,
        words=len(words),
        nonempty_lines=len(lines),
        words_per_line=wpl,
        arabic_letters=arabic_letters,
        latin_letters=latin_letters,
        long_ar_tokens=long_n,
        start_al_ratio=start_al_ratio,
        end_la_ratio=end_la_ratio,
        unlikely_start_ratio=unlikely_ratio,
        full_rtl_reversal=full_rev,
        partial_rtl_corruption=partial_rev,
        spaced_letters=spaced,
        reversed_latin=rev_lat,
        reversed_latin_tokens=rev_lat_tokens[:15],
        mirrored_parens=mirrored_parens,
        swapped_guillemets=swapped_guil,
        leading_zero_numbers=leading_zero_nums[:10],
        long_numeric_runs=long_num_runs[:10],
        many_double_quotes=many_quotes,
        quote_count=quote_count,
        fragmented_lines=fragmented,
    )


def generate_report(pages: list[PageAudit], out_md: str) -> None:
    today = _dt.date.today().isoformat()
    total = len(pages)

    per_doc = defaultdict(Counter)
    for p in pages:
        c = per_doc[p.doc]
        c["pages"] += 1
        if p.full_rtl_reversal:
            c["full_rtl_reversal"] += 1
        if p.partial_rtl_corruption:
            c["partial_rtl_corruption"] += 1
        if p.spaced_letters:
            c["spaced_letters"] += 1
        if p.reversed_latin:
            c["reversed_latin"] += 1
        if p.mirrored_parens:
            c["mirrored_parens"] += 1
        if p.swapped_guillemets:
            c["swapped_guillemets"] += 1
        if p.leading_zero_numbers:
            c["leading_zero_numbers"] += 1
        if p.long_numeric_runs:
            c["long_numeric_runs"] += 1
        if p.many_double_quotes:
            c["many_double_quotes"] += 1
        if p.fragmented_lines:
            c["fragmented_lines"] += 1

    def _abs(path: str) -> str:
        # `path` is already relative with forward slashes
        return os.path.join(os.getcwd(), path.replace("/", os.sep))

    md: list[str] = []
    md.append(f"# Arabic Output Language Audit ({today})")
    md.append("")
    md.append(f"Scope: audited **{total}** extracted page text files under `output/all_pages/**/page_*.txt`.")
    md.append("")
    md.append("This is a heuristic audit that flags high-likelihood corruption patterns.")
    md.append("")

    md.append("## Per-Document Summary")
    md.append("")
    md.append(
        "| Document | Pages | Full RTL Reversal | Partial RTL Corruption | Spaced Letters | Reversed Latin | Mirrored Parens | Swapped «» | Leading-0 Numbers | Long Numeric Runs | Many Quotes | Fragmented Lines |"
    )
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for doc, c in sorted(per_doc.items(), key=lambda kv: kv[1]["pages"], reverse=True):
        md.append(
            f"| {doc} | {c['pages']} | {c['full_rtl_reversal']} | {c['partial_rtl_corruption']} | {c['spaced_letters']} | {c['reversed_latin']} | {c['mirrored_parens']} | {c['swapped_guillemets']} | {c['leading_zero_numbers']} | {c['long_numeric_runs']} | {c['many_double_quotes']} | {c['fragmented_lines']} |"
        )
    md.append("")

    md.append("## Key Examples")
    md.append("")

    def section(
        title: str,
        items: list[PageAudit],
        *,
        key,
        limit: int = 10,
        head_lines: int | None = 8,
        extra_line=None,
    ) -> None:
        if not items:
            return
        md.append(f"### {title}")
        for p in sorted(items, key=key, reverse=True)[:limit]:
            md.append(
                f"- `{p.path}` (words/line={p.words_per_line:.2f}, ar={p.arabic_letters}, lat={p.latin_letters})"
            )
            if extra_line is not None:
                md.append(f"  - {extra_line(p)}")
            if head_lines is not None:
                md.append("  ```")
                md.append(_file_head(_abs(p.path), n=head_lines))
                md.append("  ```")
        md.append("")

    section(
        "Full RTL Reversal (selectable text is character-reversed)",
        [p for p in pages if p.full_rtl_reversal],
        key=lambda p: (p.end_la_ratio - p.start_al_ratio, p.unlikely_start_ratio),
    )
    section(
        "Partial RTL Corruption (reversed fragments inside mixed-script lines)",
        [p for p in pages if p.partial_rtl_corruption],
        key=lambda p: p.unlikely_start_ratio,
        head_lines=10,
    )
    section(
        "Spaced-Out Arabic Letters (e.g. ا ت د م ا)",
        [p for p in pages if p.spaced_letters],
        key=lambda p: p.words,  # bigger pages first
        head_lines=12,
    )
    section(
        "Reversed Latin Tokens (e.g. potS, enicaxolfixoM)",
        [p for p in pages if p.reversed_latin],
        key=lambda p: len(p.reversed_latin_tokens),
        head_lines=0,
        extra_line=lambda p: "tokens: " + ", ".join(p.reversed_latin_tokens),
    )
    section(
        "Mirrored Parentheses (e.g. )1977( )DCI(",
        [p for p in pages if p.mirrored_parens],
        key=lambda p: p.words,
        head_lines=12,
    )
    section(
        "Swapped Guillemets (» ... «)",
        [p for p in pages if p.swapped_guillemets],
        key=lambda p: p.words,
        head_lines=12,
    )
    section(
        "Suspicious Leading-Zero Numbers / Placeholder Amounts",
        [p for p in pages if p.leading_zero_numbers],
        key=lambda p: len(p.leading_zero_numbers),
        head_lines=12,
        extra_line=lambda p: "numbers: " + ", ".join(p.leading_zero_numbers),
    )
    section(
        "Long Numeric Concatenations (missing separators between columns)",
        [p for p in pages if p.long_numeric_runs],
        key=lambda p: len(p.long_numeric_runs),
        head_lines=20,
        extra_line=lambda p: "runs: " + ", ".join(p.long_numeric_runs),
    )
    section(
        "Pages with Heavy Quote Placeholders (>= 50 double quotes)",
        [p for p in pages if p.many_double_quotes],
        key=lambda p: p.quote_count,
        head_lines=20,
        extra_line=lambda p: f"quote_count={p.quote_count}",
    )
    section(
        "Severe Line Fragmentation (low words-per-line)",
        [p for p in pages if p.fragmented_lines],
        key=lambda p: (-p.words_per_line),
        head_lines=25,
    )

    md.append("## All Flagged Pages")
    md.append("")

    def list_paths(title: str, items: list[PageAudit]) -> None:
        if not items:
            return
        md.append(f"### {title} ({len(items)})")
        for p in sorted(items, key=lambda x: (x.doc, x.path)):
            md.append(f"- `{p.path}`")
        md.append("")

    list_paths("Full RTL Reversal", [p for p in pages if p.full_rtl_reversal])
    list_paths("Partial RTL Corruption", [p for p in pages if p.partial_rtl_corruption])
    list_paths("Spaced-Out Letters", [p for p in pages if p.spaced_letters])
    list_paths("Reversed Latin Tokens", [p for p in pages if p.reversed_latin])
    list_paths("Mirrored Parentheses", [p for p in pages if p.mirrored_parens])
    list_paths("Swapped Guillemets", [p for p in pages if p.swapped_guillemets])
    list_paths("Leading-Zero Numbers", [p for p in pages if p.leading_zero_numbers])
    list_paths("Long Numeric Runs", [p for p in pages if p.long_numeric_runs])
    list_paths("Heavy Quote Placeholders", [p for p in pages if p.many_double_quotes])
    list_paths("Fragmented Lines", [p for p in pages if p.fragmented_lines])

    md.append("## Interpretation (Likely Causes)")
    md.append("")
    md.append(
        "- **Full RTL reversal**: PDF has a selectable text layer, but Arabic glyph order/encoding is wrong; extraction returns reversed tokens."
    )
    md.append(
        "- **Partial RTL corruption + reversed Latin + mirrored parentheses**: mixed RTL/LTR runs in tables or inline annotations; extraction preserves bidi ordering artifacts."
    )
    md.append(
        "- **Spaced letters**: table/list text arrives as very small spans (sometimes per-character), and reconstruction doesn't re-join them."
    )
    md.append(
        "- **Numeric concatenations**: table column boundaries were lost, so adjacent amounts got concatenated without spaces."
    )
    md.append("")

    md.append("## Recommended Fixes (Prioritized)")
    md.append("")
    md.append(
        "1. Add a **scrambled-Arabic detector** before trusting selectable text and force OCR when triggered (even if a text layer exists)."
    )
    md.append(
        "2. Add a **bidi normalizer/post-processor** for mixed-script output: fix `)X(` -> `(X)`, reverse obvious reversed-Latin tokens, and normalize swapped guillemets when safe."
    )
    md.append(
        "3. Join **spaced Arabic letters** conservatively for long runs like `ا ت د م ا` (only when surrounded by Arabic context)."
    )
    md.append(
        "4. Improve **table numeric formatting**: insert separators between adjacent numeric runs when geometry indicates column boundaries (or post-process very long numeric runs)."
    )
    md.append("")
    md.append(
        "Limitations: this audit cannot reliably detect subtle OCR typos (ح/خ), missing lines, or wrong reading-order without either ground-truth text or a clean OCR comparison."
    )
    md.append("")

    os.makedirs(os.path.dirname(out_md), exist_ok=True)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-dir",
        default=os.path.join("output", "all_pages"),
        help="Directory containing per-document folders with page_*.txt files.",
    )
    parser.add_argument(
        "--out-md",
        default=os.path.join(
            "output",
            "reports",
            f"arabic_language_audit_{_dt.date.today().isoformat()}.md",
        ),
        help="Output Markdown report path.",
    )
    args = parser.parse_args()

    txt_paths = sorted(glob.glob(os.path.join(args.input_dir, "**", "page_*.txt"), recursive=True))
    pages = [audit_page(p) for p in txt_paths]
    generate_report(pages, args.out_md)
    print(args.out_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
