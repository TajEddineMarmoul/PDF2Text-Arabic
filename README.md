# pdfarabic

Arabic PDF text extraction built on PyMuPDF. Fixes ligature decomposition, RTL ordering, table extraction, and other issues that make raw PyMuPDF output unusable for Arabic.

## What it fixes

| # | Problem | Fix |
|---|---------|-----|
| 1 | **Ligature decomposition** — PyMuPDF breaks Arabic ligatures (الله, لأ, لإ) into LTR-ordered zero-width chars | Detects zero-width clusters, reverses to RTL order |
| 1b | **Lam-Alef swap** — لا ligature decomposed as ال (alef before lam) | Detects width ratio, swaps to correct order |
| 2 | **Presentation Forms** — Returns U+FB50–FDFF / U+FE70–FEFF instead of standard Arabic | NFKC normalization |
| 3 | **Line splitting** — One visual line split into multiple rawdict lines at same y | Y-coordinate merging with tolerance |
| 4 | **Number reversal** — RTL sorting reverses digit sequences (2019 → 9102) | Detects LTR digit runs, reverses back |
| 5 | **Arabic↔digit spacing** — No space between Arabic text and numbers | Regex-inserts spaces at boundaries |
| 6 | **Artifact spaces** — Space chars with overlapping bboxes cause false word breaks | Only honors spaces with physical gaps > 0.5px |
| 7 | **Invisible chars** — Zero-width joiners, BOM, LTR/RTL marks, kashida | Stripped in post-processing |

## Install

```bash
pip install .
# or with uv
uv pip install .
```

## Quick start

### Python API

```python
from pdfarabic import extract_pdf, extract_page

# Extract entire PDF
text = extract_pdf("document.pdf")

# With cropping (remove headers/page numbers)
text = extract_pdf("document.pdf", crop_top=50, crop_bottom=30)

# Crop by percentage
text = extract_pdf("document.pdf", crop_top=5, crop_bottom=3, crop_unit="pct")

# Disable footnote separator detection
text = extract_pdf("document.pdf", detect_footer=False)
```

### Single page

```python
import fitz
from pdfarabic import extract_page

doc = fitz.open("document.pdf")
text = extract_page(doc[0], crop_top=50, crop_bottom=30)
doc.close()
```

### CLI

```bash
# Process all PDFs in a directory
pdfarabic -i ./download -o ./output/plain_text

# Single file
pdfarabic -f document.pdf -o ./output

# With cropping
pdfarabic -i ./download --crop-top 50 --crop-bottom 30

# Crop by percentage, no footer detection
pdfarabic -i ./download --crop-top 5 --crop-bottom 3 --crop-unit pct --no-footer
```

## API reference

### `extract_pdf(pdf_path, **kwargs) → str`

Extract text from all pages of a PDF.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `pdf_path` | `str` | — | Path to the PDF file |
| `crop_top` | `float` | `0` | Crop from top of each page |
| `crop_bottom` | `float` | `0` | Crop from bottom of each page |
| `crop_unit` | `"px" \| "pct"` | `"px"` | Unit: points or percentage of page height |
| `detect_footer` | `bool` | `True` | Auto-detect footnote separator lines and exclude content below |

### `extract_page(page, **kwargs) → str`

Extract text from a single `fitz.Page`. Same parameters as `extract_pdf` (except `pdf_path`).

## Features

### Table extraction

Tables are automatically detected via PyMuPDF's `find_tables()`, extracted with proper Arabic cell ordering, and formatted as pipe-delimited text. Merged cells are filled down so every row is self-contained:

```
الجهات | عدد المقاعد | مقر الدائرة الانتخابية
طنجة – تطوان – الحسيمة | 2 | ولاية جهة فاس - مكناس
الشرق | 2 | ولاية جهة فاس - مكناس
فاس - مكناس | 2 | ولاية جهة فاس - مكناس
```

### Footer detection

Automatically detects horizontal separator lines (both vector drawings and text-based dashes) in the bottom 40% of each page and excludes footnote text below them. Handles non-selectable drawn lines and selectable `------` text.

### Page cropping

Crop headers and page numbers by fixed pixel amount or percentage of page height.

## Project structure

```
pdfarabic/
├── __init__.py    # Public API: extract_pdf, extract_page
├── _chars.py      # Character-level ligature/overlap fixes
├── _text.py       # RTL text building, cleaning, line merging
├── _tables.py     # Table detection and formatting
├── _footer.py     # Footer separator detection
├── _extract.py    # Page/PDF extraction orchestration
└── cli.py         # CLI entry point
```

## Integration with other projects

```bash
# Install as dependency (editable for development)
pip install -e /path/to/pdfarabic

# Or in pyproject.toml
# dependencies = ["pdfarabic @ file:///path/to/pdfarabic"]
```

```python
from pdfarabic import extract_pdf

def extract_law_text(path: str) -> str:
    return extract_pdf(path, crop_top=50, crop_bottom=30, detect_footer=True)
```
