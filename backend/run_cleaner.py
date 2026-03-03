#!/usr/bin/env python3
"""
run_cleaner.py – CLI entry-point for the legal-text cleaning pipeline.

This is a thin wrapper around :mod:`legal_cleaner`.  All business logic
lives inside the ``legal_cleaner`` package; this file only handles
argument parsing and logging setup.

Usage
-----
    # Batch-process every PDF in sources/
    python run_cleaner.py

    # Process a single PDF
    python run_cleaner.py --file sources/my_document.pdf

    # Override directories via CLI flags
    python run_cleaner.py --sources-dir /data/pdfs --output-dir /data/clean

    # Or set them in .env (see .env.example)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from legal_cleaner.config import SOURCES_DIR, OUTPUT_DIR, setup_logging
from legal_cleaner.pipeline import process_pdf, process_batch


def main() -> None:
    """Parse CLI arguments and run the appropriate pipeline mode."""
    setup_logging()

    parser = argparse.ArgumentParser(
        description="Clean Kenyan legal PDF text for RAG ingestion.",
    )
    parser.add_argument(
        "--file", "-f",
        type=Path,
        help="Path to a single PDF to process (skip batch mode).",
    )
    parser.add_argument(
        "--sources-dir", "-s",
        type=Path,
        default=SOURCES_DIR,
        help=f"Directory containing source PDFs (default: {SOURCES_DIR}).",
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Directory for cleaned output (default: {OUTPUT_DIR}).",
    )
    args = parser.parse_args()

    # ── Single-file mode ─────────────────────────────────────────────
    if args.file:
        if not args.file.exists():
            print(f"Error: file not found – {args.file}", file=sys.stderr)
            sys.exit(1)
        process_pdf(args.file, args.output_dir)
        return

    # ── Batch mode ───────────────────────────────────────────────────
    results = process_batch(args.sources_dir, args.output_dir)
    if not results:
        sys.exit(0)


if __name__ == "__main__":
    main()
