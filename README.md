# PDF2Text-Arabic

Arabic-first PDF extraction for official documents, legal texts, financial laws, scanned pages, mixed Arabic/French tables, and footnote-heavy PDFs.

The library is built on PyMuPDF, then adds Arabic-specific layout repair: RTL reading order, ligature cleanup, table reconstruction, footnote/footer cropping, page-header cropping, and optional full-page OCR for image-only or mixed pages.

## Why This Exists

Raw PDF text extraction is usually not enough for Arabic documents. Common failures include reversed words, broken `لا` / `الله` ligatures, split Arabic rows, missing superscript references, false table merges, footers mixed into body text, and scanned pages returning almost nothing.

`pdf2text-arabic` focuses on producing text that is useful for search, RAG, legal analysis, and automation.

## Feature Showcase

### Full-page and long table extraction

Large official tables are extracted as pipe-separated rows instead of markdown tables. This is easier for downstream parsers and LLM pipelines because empty cells remain explicit.

<img src="assets/showcase_full_page_table.png" width="560" alt="Full-page Arabic table extraction" />

### Side-by-side tables and article text

The extractor keeps independent table regions separate instead of merging the whole page into one bad grid.

<img src="assets/showcase_side_by_side_tables.png" width="560" alt="Side-by-side table extraction" />

### Embedded tables inside legal articles

Small tables inside normal prose are detected without converting the surrounding article into a table.

<img src="assets/showcase_embedded_table.png" width="560" alt="Embedded table in legal text" />

### Footnote and footer removal

Superscript reference tips are matched to footer reference lines. The detected footer area is excluded from the body output.

<img src="assets/showcase_footnotes.png" width="560" alt="Footnote detection and footer crop" />

### OCR detection for scanned/image pages

When `on_empty="auto"` sees a page or region that requires OCR, the page is sent to Gemini OCR instead of mixing weak selectable text with OCR text.

<img src="assets/showcase_full_page_ocr.png" width="560" alt="Full-page OCR trigger" />

For debugging, image-only regions can also be shown without forcing OCR:

<img src="assets/showcase_image_regions.png" width="560" alt="Image-only region detection" />

## What It Fixes

| Problem | What the library does |
|---|---|
| Broken Arabic ligatures | Repairs decomposed ligatures and lam-alef ordering. |
| Arabic presentation forms | Normalizes presentation-form characters to standard Arabic. |
| Wrong RTL order | Reorders characters, spans, rows, and blocks for Arabic reading order. |
| Reversed digit sequences | Keeps numeric runs such as `2023`, `1.14.44`, and money values readable. |
| Split visual rows | Merges PyMuPDF raw lines that visually belong to one row. |
| Mixed Arabic/French text | Preserves Arabic base direction while keeping Latin and numbers usable. |
| Tables with weak borders | Falls back to targeted table detection when default PyMuPDF misses rows. |
| Side-by-side tables | Uses physical bounding boxes to avoid page-wide table merges. |
| Footnotes and references | Detects superscript tips and crops matching footer reference blocks. |
| Scanned/image pages | Supports `warn`, `ignore`, `auto`, and `ocr` behavior for image-only content. |
| Debugging extraction | Renders color-coded overlays showing text, tables, OCR regions, and footer crops. |

## Install

```bash
pip install pdf2text-arabic
```

From source:

```bash
pip install .
# or
uv pip install .
```

Python `>=3.13` is required by the current package configuration.

## Quick Start

### Extract a PDF

```python
from pdf2text_arabic import extract_pdf

text = extract_pdf("document.pdf")
print(text)
```

### Extract with the recommended defaults explicitly

```python
from pdf2text_arabic import extract_pdf

text = extract_pdf(
    "document.pdf",
    crop_top=8.0,
    crop_bottom=4.5,
    crop_unit="pct",
    detect_footer=True,
    on_empty="warn",
)
```

### Extract one page

`extract_page()` returns `(text, last_table_state)`.

```python
import fitz
from pdf2text_arabic import extract_page

with fitz.open("document.pdf") as doc:
    text, _ = extract_page(doc[0])

print(text)
```

### Structured result for automation

Use this when an agent or pipeline needs warnings and page-level metadata.

```python
from pdf2text_arabic import extract_pdf_result

result = extract_pdf_result("document.pdf", on_empty="warn")

print(result.pages_total)
print(result.pages_with_text)
print(result.empty_pages)
print(result.mixed_pages)
print(result.warnings)
print(result.text)
```

### CLI

```bash
# Process every PDF in ./download into ./output/plain_text
pdf2text-arabic -i ./download -o ./output/plain_text

# Process a single file
pdf2text-arabic -f document.pdf -o ./output/plain_text

# Disable footer detection
pdf2text-arabic -f document.pdf --no-footer

# Force OCR behavior for image pages
pdf2text-arabic -f scanned.pdf --on-empty auto
```

## OCR Modes

`on_empty` controls how image-only or mixed pages are handled.

| Mode | Behavior |
|---|---|
| `warn` | Default. Warns/skips pages that need OCR instead of silently returning bad text. |
| `ignore` | Keeps selectable text behavior and does not call OCR. Useful for debugging. |
| `auto` | If a page has image-only content, sends the cropped full page to OCR. |
| `ocr` | Forces OCR for the cropped full page. |

OCR uses Gemini through `google-genai`. Set `GEMINI_API_KEY` in the environment or `.env` before using `auto` or `ocr`.

```bash
set GEMINI_API_KEY=your_key_here
pdf2text-arabic -f scanned.pdf --on-empty auto
```

```python
from pdf2text_arabic import extract_pdf, get_capabilities

caps = get_capabilities()
if caps["ocr"]:
    text = extract_pdf("scanned.pdf", on_empty="auto")
else:
    text = extract_pdf("scanned.pdf", on_empty="warn")
```

## Table Output Format

Tables are written as plain rows using ` | ` separators.

```text
الوزارة أو المؤسسة | عدد المناصب المالية
وزارة الداخلية | 7.544
إدارة الدفاع الوطني | 7.000
وزارة الصحة والحماية الاجتماعية | 5.500
```

This is intentionally not markdown. It is a stable separator format for RAG and data pipelines:

- Empty cells are visible as consecutive separators.
- Rows stay self-contained.
- Complex Arabic/French/numeric cells remain in text form.
- The extractor avoids inventing headers when the PDF does not have reliable headers.

## Footer Detection

Footer detection uses multiple signals:

- Superscript reference tips in the body.
- Matching footer lines such as `167 - ...`.
- Separator rules drawn as vectors or text.
- Same-font footer backtracking when footer text starts above the first numbered line.

If no real tip exists, the extractor avoids cropping based on separators alone. This protects pages where `---`, `___`, or dotted rows are part of the body or a table.

## Debug Overlay

Use the debug renderer to understand extraction decisions visually.

```python
import fitz
from pdf2text_arabic.debug import get_debug_pixmap

with fitz.open("document.pdf") as doc:
    pix = get_debug_pixmap(doc[0], dpi=120, on_empty="auto")
    pix.save("debug_page_001.png")
```

Overlay colors:

| Color | Meaning |
|---|---|
| Blue | Detected table region. |
| Cyan | Footer/reference area cropped from body output. |
| Magenta | Image-only/OCR region or full-page OCR selection. |
| Maroon | Superscript reference tip. |
| Orange | Wide text row. |
| Green | Right-column text row. |
| Red | Left-column text row or heading/article block. |
| Grey | Header/footer page crop band. |

## API Reference

### `extract_pdf(pdf_path, **kwargs) -> str`

Extract all pages and return one text string.

| Parameter | Type | Default | Description |
|---|---|---:|---|
| `pdf_path` | `str` | required | PDF path. |
| `crop_top` | `float` | `8.0` | Crop amount from the top. |
| `crop_bottom` | `float` | `4.5` | Crop amount from the bottom. |
| `crop_unit` | `"px" | "pct"` | `"pct"` | Crop values as points or page-height percent. |
| `auto_crop_top` | `bool` | `True` | Auto-adjust top crop for repeated headers/page numbers. |
| `auto_crop_bottom` | `bool` | `True` | Auto-adjust bottom crop for page numbers. |
| `detect_footer` | `bool` | `True` | Detect and remove footnote/reference footers. |
| `on_empty` | `"ignore" | "warn" | "auto" | "ocr"` | `"warn"` | OCR/image-page handling. |
| `table_strategy` | `str | None` | `None` | Optional PyMuPDF table strategy, e.g. `"lines"`, `"text"`. |
| `gemini_model` | `str` | `"gemini-3-flash-preview"` | Gemini model for OCR. |

### `extract_page(page, **kwargs) -> tuple[str, dict | None]`

Extract one `fitz.Page`. It accepts the same extraction options except `pdf_path`.

### `extract_pdf_result(pdf_path, **kwargs) -> ExtractionResult`

Returns structured metadata:

- `text`
- `pages_total`
- `pages_with_text`
- `empty_pages`
- `mixed_pages`
- `warnings`

### `get_capabilities() -> dict`

Reports optional runtime features such as OCR availability.

```python
from pdf2text_arabic import get_capabilities

print(get_capabilities())
```

## Project Structure

```text
pdf2text_arabic/
├── __init__.py    # Public API
├── _extract.py    # Page/PDF extraction orchestration
├── _footer.py     # Footnote/footer detection
├── _ocr.py        # Gemini OCR backend
├── _tables.py     # Table detection and pipe-format output
├── _text.py       # RTL text building and line merging
└── debug.py       # Visual debug overlay renderer
```

## Practical Guidance

- Use `extract_pdf_result()` for agents and automation.
- Use `on_empty="warn"` when OCR is not configured.
- Use `on_empty="auto"` when `GEMINI_API_KEY` is configured and scanned pages matter.
- Keep `detect_footer=True` for official legal documents with numbered references.
- Disable footer detection only if you explicitly need footnotes mixed into the body.
- Use debug PNGs before changing extraction thresholds; many issues are layout-specific.

## Development Notes

The test/debug workflow used during development is intentionally visual:

```bash
python test_all_pages.py
```

This renders per-page `.txt` and debug `.png` files under `output/all_pages/` for manual review.

Generated `output/` and `download/` folders are ignored by git. Curated README images live in `assets/`.
