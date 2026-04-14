"""OCR backends and dispatch for scanned/image regions.

Two backends are supported:

* ``"ollama"`` — local DeepSeek-OCR via the Ollama server. Output is post-
  processed to strip grounding tags and convert HTML tables to RAG blocks.
* ``"gemini"`` — Google Gemini multimodal API. The prompt instructs Gemini
  to emit the RAG ``---`` block format directly, so no post-processing is
  needed. Requires ``GEMINI_API_KEY`` in the environment or a ``.env`` file
  (loaded via ``python-dotenv`` if installed).
"""

from __future__ import annotations

import re
from typing import Literal

import fitz

from ._tables import html_to_rag_text


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
Strictly ignore and DO NOT extract any footnotes at the bottom of the page. You must also ignore and remove any superscript footnote markers (e.g., ¹, ², ³) embedded within the main text. Ignore all page headers, page numbers, and stamps. Only extract the core body content."""


def ollama_available() -> bool:
    """Return True if ollama library is installed."""
    try:
        import ollama  # noqa: F401

        return True
    except ImportError:
        return False


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


def clean_deepseek_output(text: str) -> str:
    """Removes grounding tags, coordinate markers, and OCR artifacts."""
    text = re.sub(r"<\|ref\|>.*?<\|/ref\|>", "", text)
    text = re.sub(r"<\|det\|>.*?<\|/det\|>", "", text)
    text = re.sub(r"<\|.*?\|>", "", text)
    return text.strip()


def _deepseek_ocr_page(
    page,
    regions: list[fitz.Rect],
) -> list[tuple[float, str]]:
    """Run DeepSeek-OCR via Ollama on specific image regions of a page.

    Uses grounding mode for high precision and converts HTML tables to RAG format.
    """
    import ollama

    results: list[tuple[float, str]] = []

    for idx, region in enumerate(regions):
        pix = page.get_pixmap(clip=region, dpi=300)
        debug_name = f"ocr_surgical_crop_{idx}.png"
        pix.save(debug_name)

        img_bytes = pix.tobytes("png")

        try:
            response = ollama.generate(
                model="deepseek-ocr:latest",
                prompt="<|grounding|>Extract the document text and tables. Ignore headers, footers, and page numbers.",
                images=[img_bytes],
                stream=False,
                options={"temperature": 0, "num_predict": 2048, "repeat_penalty": 1.5},
            )

            raw_text = response.get("response", "")
            if not raw_text:
                continue

            cleaned_text = clean_deepseek_output(raw_text)
            rag_text = html_to_rag_text(cleaned_text)

            if rag_text.strip():
                results.append((region.y0, rag_text.strip()))

        except Exception as exc:
            raise RuntimeError(f"Ollama OCR failed for region: {exc}") from exc

    return results


def _gemini_ocr_page(
    page,
    regions: list[fitz.Rect],
    *,
    model: str = DEFAULT_GEMINI_MODEL,
) -> list[tuple[float, str]]:
    """Run Gemini OCR on specific image regions of a page.

    Gemini emits the RAG ``---`` block format directly (per the prompt), so
    no HTML-table post-processing is applied.
    """
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
        debug_name = f"ocr_surgical_crop_{idx}.png"
        pix.save(debug_name)

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


def run_ocr(
    page,
    regions: list[fitz.Rect],
    *,
    backend: Literal["ollama", "gemini"] = "ollama",
    gemini_model: str = DEFAULT_GEMINI_MODEL,
) -> list[tuple[float, str]]:
    """OCR a page's image regions using the selected backend.

    Args:
        page: PyMuPDF page.
        regions: Image regions to OCR.
        backend: ``"ollama"`` (DeepSeek-OCR local) or ``"gemini"`` (Google).
        gemini_model: Model id used when ``backend="gemini"``.

    Returns extracted text tuples, or empty list if OCR fails.
    """
    if backend == "ollama":
        if not ollama_available():
            raise RuntimeError(
                "OCR requested but 'ollama' library is not installed or accessible. "
                "Please install it and ensure Ollama is running."
            )
        return _deepseek_ocr_page(page, regions)

    if backend == "gemini":
        if not gemini_available():
            raise RuntimeError(
                "OCR requested but 'google-genai' is not installed. "
                "Install with: pip install google-genai python-dotenv"
            )
        return _gemini_ocr_page(page, regions, model=gemini_model)

    raise ValueError(f"Unknown OCR backend: {backend!r}")
