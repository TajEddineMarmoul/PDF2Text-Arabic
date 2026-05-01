"""Arabic PDF text extraction with PyMuPDF ligature and RTL fixes.

Usage:
    from pdf2text_arabic import extract_pdf, extract_page, extract_pdf_result

    text = extract_pdf("document.pdf")
"""

from ._extract import (
    ExtractionResult,
    InvalidPDFPathError,
    OCRUnavailableError,
    OcrStrategy,
    PDFArabicError,
    extract_page,
    extract_pdf,
    extract_pdf_result,
    get_capabilities,
)
from .cli import main

__all__ = [
    "extract_pdf",
    "extract_pdf_result",
    "extract_page",
    "get_capabilities",
    "OcrStrategy",
    "ExtractionResult",
    "PDFArabicError",
    "InvalidPDFPathError",
    "OCRUnavailableError",
    "main",
]
