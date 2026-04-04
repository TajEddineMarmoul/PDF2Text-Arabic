"""Arabic PDF text extraction with PyMuPDF ligature and RTL fixes.

Usage:
    from pdfarabic import extract_pdf, extract_page

    text = extract_pdf("document.pdf")
"""

from ._extract import extract_page, extract_pdf
from .cli import main

__all__ = ["extract_pdf", "extract_page", "main"]
