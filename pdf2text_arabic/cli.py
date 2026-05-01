"""Command-line interface for Arabic PDF extraction."""

import argparse
import logging
import os
import sys

from ._extract import extract_pdf


def main():
    parser = argparse.ArgumentParser(
        description="Extract Arabic text from PDFs using PyMuPDF."
    )
    parser.add_argument(
        "-i",
        "--input-dir",
        default="./download",
        help="Directory containing PDF files (default: ./download)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default="./output/plain_text",
        help="Directory to write .txt files (default: ./output/plain_text)",
    )
    parser.add_argument(
        "-f",
        "--file",
        help="Process a single PDF file instead of a directory.",
    )
    parser.add_argument(
        "--crop-top",
        type=float,
        default=0.0,
        help="Crop from top of each page (default: 0.0).",
    )
    parser.add_argument(
        "--crop-bottom",
        type=float,
        default=0.0,
        help="Crop from bottom of each page (default: 0.0).",
    )
    parser.add_argument(
        "--crop-unit",
        choices=["px", "pct"],
        default="pct",
        help="Unit for crop values: 'px' (points) or 'pct' (percent) (default: pct).",
    )
    parser.add_argument(
        "--no-auto-crop-top",
        action="store_true",
        help="Disable automatic detection and cropping of page numbers at the top.",
    )
    parser.add_argument(
        "--no-auto-crop-bottom",
        action="store_true",
        help="Disable automatic detection and cropping of page numbers at the bottom.",
    )
    parser.add_argument(
        "--no-footer",
        action="store_true",
        help="Disable automatic footnote separator detection.",
    )
    parser.add_argument(
        "--ocr-strategy",
        choices=["never", "warn", "auto", "force"],
        default="auto",
        help=(
            "OCR decision strategy: "
            "'never' (do not call OCR), "
            "'warn' (log + skip), "
            "'auto' (OCR only when the page looks unreliable), "
            "'force' (OCR every page). "
            "Default: auto."
        ),
    )
    parser.add_argument(
        "--table-strategy",
        choices=["lines", "lines_strict", "text"],
        default=None,
        help="PyMuPDF table detection strategy. Use 'text' for tables without borders.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING,
        format="  ⚠ %(message)s",
    )

    os.makedirs(args.output_dir, exist_ok=True)

    if args.file:
        files = [(args.file, os.path.basename(args.file))]
    else:
        if not os.path.isdir(args.input_dir):
            print(f"Input directory not found: {args.input_dir}", file=sys.stderr)
            sys.exit(1)
        files = [
            (os.path.join(args.input_dir, f), f)
            for f in os.listdir(args.input_dir)
            if f.lower().endswith(".pdf")
        ]

    if not files:
        print("No PDF files found.", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(files)} PDF(s) → {args.output_dir}")

    for pdf_path, filename in files:
        try:
            text = extract_pdf(
                pdf_path,
                crop_top=args.crop_top,
                crop_bottom=args.crop_bottom,
                crop_unit=args.crop_unit,
                auto_crop_top=not args.no_auto_crop_top,
                auto_crop_bottom=not args.no_auto_crop_bottom,
                detect_footer=not args.no_footer,
                ocr_strategy=args.ocr_strategy,
                table_strategy=args.table_strategy,
            )
            out_name = os.path.splitext(filename)[0] + ".txt"
            out_path = os.path.join(args.output_dir, out_name)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"  ✓ {filename}")
        except Exception as e:
            print(f"  ✗ {filename}: {e}", file=sys.stderr)
