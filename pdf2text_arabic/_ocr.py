"""OCR backend for scanned/image regions, powered by Google Gemini.

Requires ``google-genai`` and a ``GEMINI_API_KEY`` in the environment or a
``.env`` file (loaded via ``python-dotenv`` if installed). The Gemini prompt
emits the pipeline's native RAG ``---`` block format directly, so no
post-processing is needed.
"""

from __future__ import annotations

import fitz


# Default Gemini model used for OCR. Override via ``gemini_model`` kwarg.
DEFAULT_GEMINI_MODEL = "gemini-3-flash-preview"

# Prompt for Gemini OCR that emits the pipeline's native RAG block format
# for tables (no Markdown pipes) and strips footnotes/headers/page numbers.
_GEMINI_OCR_PROMPT = """You are an expert OCR system specialized in extracting complex official Arabic documents, including legal, technical, and administrative records. Extract all Arabic text exactly as it appears without translating or summarizing. Do not auto-correct spelling.

CRITICAL TABLE INSTRUCTIONS:
Do NOT use standard Markdown table formatting (do not use the | pipe character). Instead, extract every table by representing each row as a vertical block separated by ---. Map the column header to the cell value exactly like this:
---
Header 1: [Cell Value]
Header 2: [Cell Value]
Header 3: [Cell Value]
---

If a cell is empty, do not include that line. Do not generate completely empty table rows.

EXCLUSIONS:
Strictly ignore and DO NOT extract any footnotes at the bottom of the page. You must also ignore and remove any superscript footnote markers (e.g., ¹, ², ³) embedded within the main text. Ignore all page headers, page numbers, and stamps. Only extract the core body content.

REPEATING HEADERS AND PAGE NUMBERS:
The top of each page often contains a repeating masthead or running header (e.g., "الجريدة الرسمية عدد XXXX", issue date, logos, or decorative rule lines). The bottom often contains a standalone page number (digits, sometimes wrapped like "-12-" or "(12)"). These elements are NOT body content. Skip them completely even if the geometric crop did not fully remove them. If the very first visible line is clearly a running masthead and not body prose, drop it. If the very last visible line is just a number, drop it."""


def gemini_available() -> bool:
    """Return True if the google-genai library is installed."""
    try:
        from google import genai  # noqa: F401

        return True
    except ImportError:
        return False


def load_gemini_api_key() -> str | None:
    """Return the Gemini API key, loading .env first if python-dotenv is present."""
    import os

    if not os.environ.get("GEMINI_API_KEY"):
        try:
            from dotenv import find_dotenv, load_dotenv

            load_dotenv(find_dotenv(usecwd=True))
        except ImportError:
            pass
    return os.environ.get("GEMINI_API_KEY")


def run_ocr(
    page: fitz.Page,
    regions: list[fitz.Rect],
    *,
    model: str = DEFAULT_GEMINI_MODEL,
) -> list[tuple[float, str]]:
    """Run Gemini OCR on specific image regions of a page.

    Args:
        page: PyMuPDF page.
        regions: Image regions to OCR.
        model: Gemini model id (default: ``DEFAULT_GEMINI_MODEL``).

    Returns extracted text tuples keyed by region y-top.
    """
    if not gemini_available():
        raise RuntimeError(
            "OCR requested but 'google-genai' is not installed. "
            "Install with: pip install google-genai python-dotenv"
        )

    from google import genai
    from PIL import Image
    import io

    api_key = load_gemini_api_key()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to your .env or environment."
        )

    client = genai.Client(api_key=api_key)
    results: list[tuple[float, str]] = []

    for idx, region in enumerate(regions):
        pix = page.get_pixmap(clip=region, dpi=300)

        img = Image.open(io.BytesIO(pix.tobytes("png")))

        try:
            response = client.models.generate_content(
                model=model,
                contents=[_GEMINI_OCR_PROMPT, img],
            )
            text = (response.text or "").strip()
            if text:
                results.append((region.y0, text))
        except Exception as exc:
            raise RuntimeError(f"Gemini OCR failed for region: {exc}") from exc

    return results
