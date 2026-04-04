"""Page-level and PDF-level Arabic text extraction."""

import fitz

from ._tables import extract_tables
from ._text import build_row_text, clean_arabic, merge_lines_by_y

fitz.TOOLS.set_small_glyph_heights(True)


def extract_page(page) -> str:
    """Extract corrected Arabic text from one PyMuPDF page."""
    table_entries, t_bboxes = extract_tables(page)

    rawdict = page.get_text("rawdict")
    pieces: list[tuple[float, str]] = []

    for block in rawdict["blocks"]:
        if "lines" not in block:
            continue

        bx0, by0, bx1, by1 = block["bbox"]
        in_table = False
        for tx0, ty0, tx1, ty1 in t_bboxes:
            bcx = (bx0 + bx1) / 2
            bcy = (by0 + by1) / 2
            if tx0 <= bcx <= tx1 and ty0 <= bcy <= ty1:
                in_table = True
                break
        if in_table:
            continue

        rows = merge_lines_by_y(block["lines"])
        rows.sort(key=lambda r: r["cy"])

        lines_text: list[str] = []
        for row in rows:
            text = build_row_text(row["spans"])
            text = clean_arabic(text).strip()
            if text:
                lines_text.append(text)

        if lines_text:
            pieces.append((by0, "\n".join(lines_text)))

    for y_top, ttext in table_entries:
        pieces.append((y_top, ttext))

    pieces.sort(key=lambda p: p[0])

    return "\n\n".join(text for _, text in pieces)


def extract_pdf(
    pdf_path: str,
    ocr_if_needed: bool = False,
    ocr_language: str = "ara",
) -> str:
    """Extract Arabic text from a PDF file.

    Args:
        pdf_path: Path to the PDF file.
        ocr_if_needed: Fall back to OCR if a page has no extractable text.
        ocr_language: Tesseract language code for OCR fallback.

    Returns:
        The full extracted text with pages separated by double newlines.
    """
    doc = fitz.open(pdf_path)
    pages: list[str] = []
    for page in doc:
        text = extract_page(page)
        if not text.strip() and ocr_if_needed:
            try:
                tp = page.get_textpage_ocr(language=ocr_language, dpi=300, full=True)
                text = clean_arabic(page.get_text("text", textpage=tp))
            except Exception:
                pass
        if text.strip():
            pages.append(text)
    doc.close()
    return "\n\n".join(pages)
