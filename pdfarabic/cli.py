"""Command-line interface for Arabic PDF extraction."""

import argparse
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
        "--ocr",
        action="store_true",
        help="Enable OCR fallback for pages with no extractable text.",
    )
    args = parser.parse_args()

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
            text = extract_pdf(pdf_path, ocr_if_needed=args.ocr)
            out_name = os.path.splitext(filename)[0] + ".txt"
            out_path = os.path.join(args.output_dir, out_name)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"  ✓ {filename}")
        except Exception as e:
            print(f"  ✗ {filename}: {e}", file=sys.stderr)
